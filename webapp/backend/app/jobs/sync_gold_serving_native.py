"""
Delta Lake (gold) -> CockroachDB serving-table sync job.

Reads the gold `risk_scores` Delta table on HDFS with delta-rs (no JVM/Spark):
  * first run  : snapshot load (only rows with risk_score >= RISK_THRESHOLD_MEDIUM),
  * later runs : incremental read of the Change Data Feed (CDF), 25 commits at a time,
and upserts the rows into the `transactions` table. Progress is stored in
`sync_checkpoints` after every CDF segment, so the job can be stopped and restarted safely.

Values are copied exactly as stored in Delta (latency_ms, received_at, prediction_label, ...).
Columns that are absent or null in Delta stay NULL here, except `amount`, which is NOT NULL in the
serving table (rows with a missing amount are stored as 0.0 and counted in a warning).

Usage:
  python -m app.jobs.sync_gold_serving_native                 # one pass, then exit
  python -m app.jobs.sync_gold_serving_native --loop          # run until stopped (default every 2 s)
  python -m app.jobs.sync_gold_serving_native --loop --interval 1
Stop a looping job with:  kill -15 <PID>   (it finishes the current CDF segment, then exits).
Only one instance can run at a time (lock file /tmp/sync_gold_serving.lock).
"""
import argparse
import fcntl
import json
import os
import signal
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.config.settings import settings
from app.database.session import engine

CDF_VERSION_STEP = 25
LOCK_PATH = "/tmp/sync_gold_serving.lock"
PID_PATH = "/tmp/sync_gold_serving.pid"
HEARTBEAT_SECONDS = 60

TARGET_COLUMNS = [
    "transaction_id", "source_account", "dest_account", "trans_type", "amount", "channel",
    "timestamp", "received_at", "risk_score", "prediction_label", "model_version",
    "latency_ms", "inspection_status", "top_risk_factors", "delta_commit_version",
]

_STOP = threading.Event()


def _request_stop(signum, _frame) -> None:
    print(f"[Sync] Signal {signum} received: finishing the current segment, then stopping.", flush=True)
    _STOP.set()


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _serialize_factors(val: Any) -> Optional[str]:
    """Serialize top_risk_factors to a JSON string (None when empty)."""
    if val is None:
        return None
    if isinstance(val, dict):
        return json.dumps(val, default=str)
    if isinstance(val, (str, bytes)):
        return val.decode() if isinstance(val, bytes) else val
    if hasattr(val, "__len__"):
        return json.dumps(list(val), default=str) if len(val) > 0 else None
    return None if _is_missing(val) else str(val)


class DeltaServingSyncPipeline:
    def __init__(self, gold_table_uri: str = settings.GOLD_RISK_SCORES_PATH, target_table_name: str = "transactions"):
        self.gold_uri = gold_table_uri
        self.target_table = target_table_name
        self._ensure_checkpoint_table()

    # ---------------- checkpoint ----------------
    def _ensure_checkpoint_table(self) -> None:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sync_checkpoints (
                    table_name VARCHAR(100) PRIMARY KEY,
                    last_synced_version BIGINT NOT NULL,
                    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))

    def _get_last_checkpoint(self) -> int:
        """Last synced Delta version, or -1 when this table was never synced."""
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT last_synced_version FROM sync_checkpoints WHERE table_name = :t"),
                {"t": self.target_table},
            ).scalar()
        return int(result) if result is not None else -1

    def _save_checkpoint(self, version: int) -> None:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO sync_checkpoints (table_name, last_synced_version, last_synced_at)
                VALUES (:t, :v, CURRENT_TIMESTAMP)
                ON CONFLICT (table_name)
                DO UPDATE SET last_synced_version = :v, last_synced_at = CURRENT_TIMESTAMP;
            """), {"t": self.target_table, "v": version})

    # ---------------- transform ----------------
    @staticmethod
    def _enrich_for_transactions(df: pd.DataFrame) -> pd.DataFrame:
        """Shape a Delta dataframe to the `transactions` schema without inventing values."""
        if df.empty:
            return df

        df = df.copy()
        df["transaction_id"] = df["transaction_id"].astype(str).str.strip()

        for col in ("source_account", "dest_account", "trans_type", "channel", "model_version", "inspection_status"):
            if col not in df.columns:
                df[col] = None

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce") if "amount" in df.columns else None
        df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce") if "risk_score" in df.columns else None

        # prediction_label: copy from Delta; derive from the HIGH threshold only when Delta has no value.
        if "prediction_label" in df.columns:
            label = pd.to_numeric(df["prediction_label"], errors="coerce")
        else:
            label = pd.Series([None] * len(df), index=df.index, dtype="float64")
        derived = (df["risk_score"] >= settings.RISK_THRESHOLD_HIGH).astype("float64")
        df["prediction_label"] = label.where(label.notna(), derived)

        df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce") if "latency_ms" in df.columns else None

        if "received_at" not in df.columns:
            df["received_at"] = df["scored_at"] if "scored_at" in df.columns else None
        df["received_at"] = pd.to_datetime(df["received_at"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce") if "timestamp" in df.columns else pd.NaT

        df["top_risk_factors"] = df["top_risk_factors"].apply(_serialize_factors) if "top_risk_factors" in df.columns else None

        if "delta_commit_version" not in df.columns:
            df["delta_commit_version"] = None

        out = df[[c for c in TARGET_COLUMNS if c in df.columns]].copy()
        # `transactions.source_account` is NOT NULL: rows without it cannot be stored.
        return out[out["source_account"].notna()]

    # ---------------- run ----------------
    def run_sync(self, initial_filter_alerts_only: bool = True, quiet: bool = False,
                 skip_unreadable: bool = False) -> Dict[str, Any]:
        """One sync pass.

        quiet           : do not print the header when there is nothing to do (used by --loop).
        skip_unreadable : when a CDF segment cannot be read (e.g. a Parquet file was removed from
                          HDFS), log it, advance the checkpoint past it and continue. Rows of that
                          segment are NOT synced. Default False: the error is raised instead.
        """
        dt = DeltaTable(self.gold_uri)
        current_version = dt.version()
        last_version = self._get_last_checkpoint()
        if not quiet:
            print(f"[Sync] Source: {self.gold_uri}")
            print(f"[Sync] Target: '{self.target_table}'")
            print(f"[Sync] Delta version: {current_version}, last synced version: {last_version}")

        if last_version >= current_version:
            return {"status": "up_to_date", "current_version": current_version,
                    "last_synced_version": last_version, "records_synced": 0}

        if quiet:
            print(f"[Sync] Delta version: {current_version}, last synced version: {last_version}", flush=True)

        records_synced = 0
        skipped_segments: List[str] = []
        stopped = False

        if last_version == -1:
            # Initial snapshot
            if initial_filter_alerts_only:
                pa_table = dt.to_pyarrow_table(filters=[("risk_score", ">=", settings.RISK_THRESHOLD_MEDIUM)])
            else:
                pa_table = dt.to_pyarrow_table()
            df = pa_table.to_pandas()
            df["delta_commit_version"] = current_version
            df = self._enrich_for_transactions(df).drop_duplicates(subset=["transaction_id"], keep="last")
            records_synced = len(df)
            if not df.empty:
                self._upsert_batch(df)
            self._save_checkpoint(current_version)
            print(f"[Sync] Initial snapshot: {records_synced} rows, checkpoint {current_version} saved.")
        else:
            cur_v = max(0, last_version + 1)
            while cur_v <= current_version:
                if _STOP.is_set():
                    stopped = True
                    print(f"[Sync] Stop requested: stopped before version {cur_v}.", flush=True)
                    break
                end_v = min(current_version, cur_v + CDF_VERSION_STEP - 1)
                print(f"[Sync] Reading CDF versions {cur_v} -> {end_v} ...", flush=True)
                try:
                    changes = pa.table(dt.load_cdf(starting_version=cur_v, ending_version=end_v).read_all()).to_pandas()
                except Exception as exc:  # noqa: BLE001 - delta-rs raises generic Exception
                    if not skip_unreadable:
                        raise
                    msg = f"{cur_v}-{end_v}"
                    skipped_segments.append(msg)
                    print(f"[Sync] WARNING: segment {msg} unreadable, SKIPPED (rows not synced): "
                          f"{str(exc)[:200]}", flush=True)
                    self._save_checkpoint(end_v)
                    cur_v = end_v + 1
                    continue

                chunk_synced = 0
                if not changes.empty:
                    changes = changes[changes["_change_type"].isin(["insert", "update_postimage"])].copy()
                    if "risk_score" in changes.columns:
                        changes = changes[changes["risk_score"] >= settings.RISK_THRESHOLD_MEDIUM].copy()
                    # Keep the NEWEST change per transaction: order by commit version first.
                    if "_commit_version" in changes.columns:
                        changes = changes.sort_values("_commit_version", kind="stable")
                    changes["delta_commit_version"] = (
                        changes["_commit_version"].astype("Int64") if "_commit_version" in changes.columns else end_v
                    )
                    changes = changes.drop(columns=[c for c in ("_change_type", "_commit_version", "_commit_timestamp") if c in changes.columns])
                    changes = changes.drop_duplicates(subset=["transaction_id"], keep="last")
                    changes = self._enrich_for_transactions(changes)
                    chunk_synced = len(changes)
                    records_synced += chunk_synced
                    if not changes.empty:
                        self._upsert_batch(changes)
                self._save_checkpoint(end_v)
                print(f"[Sync] Checkpoint {end_v} saved ({chunk_synced} rows upserted).", flush=True)
                cur_v = end_v + 1

        print(f"[Sync] Done up to version {current_version} ({records_synced} rows).")
        result = {"status": "stopped" if stopped else "success", "current_version": current_version,
                  "previous_version": last_version, "records_synced": records_synced}
        if skipped_segments:
            result["skipped_segments"] = skipped_segments
        return result

    # ---------------- load ----------------
    @staticmethod
    def _to_iso(value: Any) -> Optional[str]:
        if _is_missing(value):
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        return None if _is_missing(value) else int(value)

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        return None if _is_missing(value) else float(value)

    @staticmethod
    def _to_str(value: Any) -> Optional[str]:
        return None if _is_missing(value) else str(value)

    def _upsert_batch(self, df: pd.DataFrame, page_size: int = 1000) -> None:
        """Upsert rows into the serving table. Reviewed (non-PENDING) rows are never overwritten."""
        if df.empty:
            return

        records: List[tuple] = []
        missing_amount = 0
        for row in df.itertuples(index=False):
            if _is_missing(getattr(row, "amount", None)):
                missing_amount += 1
            records.append((
                str(row.transaction_id),
                str(row.source_account),
                self._to_str(getattr(row, "dest_account", None)),
                self._to_str(getattr(row, "trans_type", None)),
                self._to_float(getattr(row, "amount", None)) or 0.0,  # `amount` is NOT NULL in the serving table
                self._to_str(getattr(row, "channel", None)),
                self._to_iso(getattr(row, "timestamp", None)),
                self._to_iso(getattr(row, "received_at", None)),
                self._to_float(getattr(row, "risk_score", None)) or 0.0,  # NOT NULL in the serving table
                self._to_int(getattr(row, "prediction_label", None)),
                self._to_str(getattr(row, "model_version", None)),
                self._to_int(getattr(row, "latency_ms", None)),
                self._to_str(getattr(row, "inspection_status", None)) or "PENDING",
                getattr(row, "top_risk_factors", None) if isinstance(getattr(row, "top_risk_factors", None), str) else None,
                self._to_int(getattr(row, "delta_commit_version", None)),
            ))
        if missing_amount:
            print(f"[Sync] WARNING: {missing_amount} row(s) had no amount in Delta; stored as 0.0 "
                  f"(column is NOT NULL).", flush=True)

        sql = f"""
            INSERT INTO {self.target_table} (
                transaction_id, source_account, dest_account, trans_type,
                amount, channel, timestamp, received_at, risk_score,
                prediction_label, model_version, latency_ms,
                inspection_status, top_risk_factors,
                delta_commit_version, updated_at
            ) VALUES %s
            ON CONFLICT (transaction_id) DO UPDATE SET
                received_at = EXCLUDED.received_at,
                risk_score = EXCLUDED.risk_score,
                prediction_label = EXCLUDED.prediction_label,
                model_version = EXCLUDED.model_version,
                latency_ms = EXCLUDED.latency_ms,
                top_risk_factors = EXCLUDED.top_risk_factors,
                delta_commit_version = EXCLUDED.delta_commit_version,
                updated_at = CURRENT_TIMESTAMP
            WHERE {self.target_table}.inspection_status IN ('PENDING', 'NEW') OR {self.target_table}.inspection_status IS NULL;
        """
        template = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, CURRENT_TIMESTAMP)"

        raw_conn = engine.raw_connection()
        try:
            for i in range(0, len(records), page_size):
                chunk = records[i:i + page_size]
                with raw_conn.cursor() as cur:
                    execute_values(cur, sql, chunk, template=template, page_size=len(chunk))
                raw_conn.commit()
        finally:
            raw_conn.close()


# ---------------- command line ----------------
def _acquire_lock():
    """Allow a single running instance. Returns the open lock file, or None if already locked."""
    handle = open(LOCK_PATH, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def _run_loop(pipeline: DeltaServingSyncPipeline, interval: float, skip_unreadable: bool, max_failures: int) -> int:
    failures = 0
    cycles = 0
    last_beat = 0.0
    print(f"[Loop] Started (PID {os.getpid()}), interval {interval}s. Stop with: kill -15 {os.getpid()}", flush=True)
    while not _STOP.is_set():
        t0 = time.monotonic()
        try:
            result = pipeline.run_sync(quiet=True, skip_unreadable=skip_unreadable)
            failures = 0
            cycles += 1
            took = time.monotonic() - t0
            now = time.monotonic()
            if result["status"] != "up_to_date":
                print(f"[Loop] cycle={cycles} status={result['status']} version={result['current_version']} "
                      f"rows={result['records_synced']} took={took:.2f}s", flush=True)
                last_beat = now
            elif now - last_beat >= HEARTBEAT_SECONDS:
                print(f"[Loop] cycle={cycles} up_to_date version={result['current_version']}", flush=True)
                last_beat = now
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[Loop] ERROR ({failures}/{max_failures}): {str(exc)[:300]}", flush=True)
            if failures >= max_failures:
                print("[Loop] Too many consecutive failures: exiting with code 1.", flush=True)
                return 1
        wait = interval if failures == 0 else min(30.0, interval * (2 ** min(failures, 5)))
        _STOP.wait(wait)
    print("[Loop] Stopped cleanly.", flush=True)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync gold risk_scores (Delta CDF) to CockroachDB.")
    parser.add_argument("--loop", action="store_true", help="run continuously until stopped (SIGTERM/SIGINT)")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between passes in --loop mode")
    parser.add_argument("--skip-unreadable", action="store_true",
                        help="skip CDF segments that cannot be read (their rows are NOT synced)")
    parser.add_argument("--max-failures", type=int, default=20,
                        help="--loop: exit after this many consecutive failed passes")
    args = parser.parse_args(argv)

    lock = _acquire_lock()
    if lock is None:
        print(f"[Sync] Another sync instance is already running (lock {LOCK_PATH}). Exiting.")
        return 1

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    try:
        pipeline = DeltaServingSyncPipeline()
        if args.loop:
            return _run_loop(pipeline, max(0.2, args.interval), args.skip_unreadable, max(1, args.max_failures))
        print("Sync result:", pipeline.run_sync(skip_unreadable=args.skip_unreadable))
        return 0
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
