# Feature calculation and state synchronization for Point-in-Time correctness
# Single Source of Truth: Ring Buffer (recent_events)
import json
import math
import pandas as pd


def _day_str(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def prune_and_sync_state(state_dict, current_ts):
    """
    Prune 3 things based on time-based cutoffs:
      1. Ring buffer events older than 30 days.
      2. unique_dest_24h_json entries older than 24 hours.
      3. hour_histogram_json daily buckets older than 30 days.
    Ring buffer IS the single source of truth — no counters to desync.
    """
    # 1. Ring buffer: pop expired events from HEAD (sorted asc)
    events = state_dict.get("recent_events", [])
    cutoff_30d = current_ts - pd.Timedelta(days=30)
    while events and pd.Timestamp(events[0]["ts"]) < cutoff_30d:
        events.pop(0)
    state_dict["recent_events"] = events

    # 2. Prune unique destinations older than 24 hours
    cutoff_24h_iso = (current_ts - pd.Timedelta(hours=24)).isoformat()
    try:
        dests = json.loads(state_dict.get("unique_dest_24h_json") or "{}")
    except Exception:
        dests = {}
    dests = {k: v for k, v in dests.items() if v >= cutoff_24h_iso}
    state_dict["unique_dest_24h_json"] = json.dumps(dests)

    # 3. Prune daily hour-histogram buckets older than 30 days
    cutoff_day = _day_str(cutoff_30d)
    try:
        daily = json.loads(state_dict.get("hour_histogram_json") or "{}")
    except Exception:
        daily = {}
    daily = {d: h for d, h in daily.items() if d >= cutoff_day}
    state_dict["hour_histogram_json"] = json.dumps(daily)


def update_unique_dest(state_dict, dest_acc, ev_ts, max_tracked=200):
    """Track first-seen timestamp of each destination in last 24h; LRU-evict when full."""
    if not dest_acc:
        return
    try:
        dests = json.loads(state_dict.get("unique_dest_24h_json") or "{}")
    except Exception:
        dests = {}
    if dest_acc not in dests:
        if len(dests) >= max_tracked:
            oldest_k = min(dests.keys(), key=lambda k: dests[k])
            del dests[oldest_k]
        dests[dest_acc] = ev_ts.isoformat()
    # If already tracked, keep the original first-seen timestamp
    state_dict["unique_dest_24h_json"] = json.dumps(dests)


def update_hour_histogram(state_dict, ev_ts):
    """Increment today's hour bucket in the daily histogram."""
    try:
        daily = json.loads(state_dict.get("hour_histogram_json") or "{}")
    except Exception:
        daily = {}
    day = _day_str(ev_ts)
    hour = str(ev_ts.hour)
    day_map = daily.get(day, {})
    day_map[hour] = day_map.get(hour, 0) + 1
    daily[day] = day_map
    state_dict["hour_histogram_json"] = json.dumps(daily)


def _get_hour_totals_30d(state_dict):
    """Sum hour counts across the last 30 days from the daily histogram."""
    try:
        daily = json.loads(state_dict.get("hour_histogram_json") or "{}")
    except Exception:
        daily = {}
    totals = {}
    for day, hours in daily.items():
        for h, c in hours.items():
            totals[h] = totals.get(h, 0) + c
    return totals


def compute_features(state_dict, recent_events, row):
    """
    Compute all PIT features strictly from ring buffer + derived maps.
    Single source of truth — 100% immune to counter drift.
    """
    ev_ts = pd.Timestamp(row["timestamp"])
    amt = float(row.get("amount") or 0.0)
    old_bal = float(row.get("old_balance_source") or 0.0)
    old_dst = float(row.get("old_balance_dest") or 0.0)

    cutoff_1h  = ev_ts - pd.Timedelta(hours=1)
    cutoff_24h = ev_ts - pd.Timedelta(hours=24)
    cutoff_7d  = ev_ts - pd.Timedelta(days=7)
    cutoff_30d = ev_ts - pd.Timedelta(days=30)

    c_1h = c_24h = c_7d = c_30d = 0
    s_24h = s_7d = s_30d = 0.0
    s_sq_30d = 0.0

    # Single-pass scan over sorted ring buffer (pre-transaction events only)
    for e in recent_events:
        e_ts = pd.Timestamp(e["ts"])
        if e_ts < cutoff_30d:
            continue
        a = float(e.get("amt") or 0.0)
        c_30d += 1
        s_30d += a
        s_sq_30d += a * a
        if e_ts >= cutoff_7d:
            c_7d += 1
            s_7d += a
            if e_ts >= cutoff_24h:
                c_24h += 1
                s_24h += a
                if e_ts >= cutoff_1h:
                    c_1h += 1

    avg_30d = (s_30d / c_30d) if c_30d > 0 else 0.0
    if c_30d > 1:
        variance = (s_sq_30d / c_30d) - (avg_30d * avg_30d)
        stddev_30d = float(max(0.0, variance) ** 0.5)
    else:
        stddev_30d = 0.0

    # Unique dest 24h from pruned map
    try:
        dests = json.loads(state_dict.get("unique_dest_24h_json") or "{}")
    except Exception:
        dests = {}
    unique_dest_24h = len(dests)

    # Hour histogram: totals across last 30 days
    hour_totals = _get_hour_totals_30d(state_dict)
    frequent_hours_sorted = sorted(hour_totals.items(), key=lambda x: -x[1])[:3]
    frequent_hours_list = [int(h) for h, _ in frequent_hours_sorted]
    hours_seen = set(int(h) for h in hour_totals.keys())

    # Previous transaction from recent_events (the last event in recent_events before ev_ts)
    if recent_events:
        prev_ev = recent_events[-1]
        prev_ts = pd.Timestamp(prev_ev["ts"])
        sec_diff = (ev_ts - prev_ts).total_seconds()
        sec_since_last = float(max(0.0, sec_diff))
        prev_amt = float(prev_ev.get("amt") or 0.0)
    else:
        sec_since_last = -1.0
        prev_amt = -1.0

    amt_ratio_prev = round(amt / prev_amt, 4) if prev_amt > 0 else 1.0
    is_rapid = 1.0 if (0.0 <= sec_since_last < 10.0) else 0.0

    # Cyclical hour
    sec_of_day = ev_ts.hour * 3600 + ev_ts.minute * 60 + ev_ts.second
    hour_cos = round(math.cos(sec_of_day * 2.0 * math.pi / 86400.0), 6)

    # Core log & differences
    log_amt = round(math.log(max(amt, 0.0) + 1.0), 4)
    amt_diff_avg = round(amt - avg_30d, 4)

    # Balance dynamics & ratios
    bal_drain_ratio = round(max(0.0, amt / old_bal), 4) if old_bal > 0 else 1.0
    rem_bal_ratio = round(max(0.0, old_bal - amt) / old_bal, 4) if old_bal > 0 else 0.0
    dest_src_ratio = round(old_dst / (old_bal + 1.0), 4)

    dest_str = str(row.get("dest_account") or "")
    dest_is_merch = 1.0 if dest_str.startswith("M") else 0.0

    trans_type_str = str(row.get("trans_type") or "UNKNOWN")
    channel_str = str(row.get("channel") or "UNKNOWN")

    is_xfer_cashout = 1.0 if trans_type_str in ("TRANSFER", "CASH_OUT") else 0.0
    is_micro = 1.0 if amt <= 5.0 else 0.0

    c_1h_to_7d_ratio = round(float(c_1h) / (float(c_7d) + 1.0), 4)
    amt_to_sum_7d = round(amt / (s_7d + 1.0), 4) if s_7d > 0 else 1.0
    amt_zscore = round((amt - avg_30d) / max(stddev_30d, 1.0), 4) if (c_30d > 1 and s_sq_30d > 0) else 0.0

    is_atm = 1.0 if (trans_type_str == "CASH_OUT" and channel_str == "ATM") else 0.0

    return {
        "amount": amt,
        "log_amount": log_amt,
        "old_balance_source": old_bal,
        "old_balance_dest": old_dst,
        "balance_drain_ratio": bal_drain_ratio,
        "remaining_balance_ratio": rem_bal_ratio,
        "dest_to_source_bal_ratio": dest_src_ratio,
        "dest_is_merchant": dest_is_merch,
        "is_micro_transaction": is_micro,
        "is_transfer_or_cashout": is_xfer_cashout,
        "trans_count_1h": float(c_1h),
        "trans_count_24h": float(c_24h),
        "trans_count_7d": float(c_7d),
        "trans_count_1h_to_7d_ratio": c_1h_to_7d_ratio,
        "sum_amount_24h": s_24h,
        "sum_amount_7d": s_7d,
        "avg_amount_30d": avg_30d,
        "stddev_amount_30d": stddev_30d,
        "unique_dest_accounts_24h": float(unique_dest_24h),
        "is_unusual_hour": 0.0 if (not hours_seen or ev_ts.hour in hours_seen) else 1.0,
        "amount_to_avg_ratio": round(amt / avg_30d, 4) if avg_30d > 0 else 1.0,
        "amount_to_sum_7d_ratio": amt_to_sum_7d,
        "amount_zscore_local": amt_zscore,
        "amount_diff_avg_30d": amt_diff_avg,
        "seconds_since_last_transaction": sec_since_last,
        "inbound_count_7d": 0.0,
        "inbound_amount_7d": 0.0,
        "inbound_to_outbound_ratio_7d": 0.0,
        "amount_to_dest_inbound_avg": 1.0,
        "prev_transaction_amount": prev_amt,
        "amount_ratio_to_prev": amt_ratio_prev,
        "is_rapid_fire": is_rapid,
        "is_atm_cashout": is_atm,
        "hour_cos": hour_cos,
        "amount_to_old_balance_ratio": round(amt / old_bal, 4) if old_bal > 0 else 999.0,
        "is_drain_attempt": 1.0 if amt >= old_bal else 0.0,
        "is_zero_dest_balance": 1.0 if old_dst == 0.0 else 0.0,
        "trans_type": trans_type_str,
        "channel": channel_str,
        "frequent_tx_hours": frequent_hours_list,
        "_c_1h": c_1h,
        "_c_24h": c_24h,
        "_c_7d": c_7d,
        "_c_30d": c_30d,
        "_s_24h": s_24h,
        "_s_7d": s_7d,
        "_s_30d": s_30d,
        "_s_sq_30d": s_sq_30d,
    }


compute_features_from_state = compute_features