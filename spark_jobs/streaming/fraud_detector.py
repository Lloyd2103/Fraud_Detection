# High-Performance Stateful Fraud Detector using applyInPandasWithState
import os
import json
import time
import pandas as pd
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from concurrent.futures import ThreadPoolExecutor
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_timestamp,
    to_date,
    current_timestamp,
    to_json,
    struct,
    array,
    unix_millis,
    when,
    lit,
    avg as spark_avg,
    max as spark_max,
    count as spark_count,
    expr,
    least,
    round,
    abs,
    coalesce,
)
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    LongType,
    TimestampType,
    ArrayType,
    IntegerType,
)
from pyspark.sql.streaming.state import GroupState, GroupStateTimeout
from pyspark.ml.functions import vector_to_array
from delta.tables import DeltaTable

from state_helpers import STATE_SCHEMA, FEATURE_OUTPUT_SCHEMA
from model_loader import get_model
from feature_builder import (
    compute_features,
    prune_and_sync_state,
    update_unique_dest,
    update_hour_histogram,
)


def clean_path(p):
    if p and p.startswith("hdfs:///"):
        return "/" + p[len("hdfs:///") :].lstrip("/")
    return p


# Configurations from .env with robust fallbacks
MODEL_PATH = clean_path(
    os.getenv("MODEL_PATH", "/lakehouse/fraud_detection/models/gbt_fraud_model")
)
CANDIDATE_PATH = clean_path(
    os.getenv("CANDIDATE_PATH", "/lakehouse/fraud_detection/models/candidate_gbt_model")
)

GOLD_RISK_SCORES = clean_path(
    os.getenv("GOLD_RISK_SCORES", "/lakehouse/fraud_detection/gold/risk_scores")
)
SILVER_CUSTOMER_STATES = clean_path(
    os.getenv(
        "SILVER_CUSTOMER_STATES", "/lakehouse/fraud_detection/silver/customer_states"
    )
)
CHECKPOINT_PATH = clean_path(
    os.getenv(
        "CHECKPOINT_RISK_SCORES",
        "/lakehouse/fraud_detection/checkpoints/risk_scores_stateful",
    )
)
KAFKA_BROKERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092,192.168.80.200:9092"
)
KAFKA_TRANSACTION_TOPIC = os.getenv("KAFKA_TRANSACTION_TOPIC") or os.getenv(
    "KAFKA_TOPIC", "transactions"
)
KAFKA_ALERTS_TOPIC = os.getenv("KAFKA_ALERTS_TOPIC", "alerts")
TXN_APP_ID = os.getenv("TXN_APP_ID", f"fraud_detector_stateful_{int(time.time())}")


STATE_TIMEOUT_DAYS = int(os.getenv("STATE_TIMEOUT_DAYS", "30"))
RING_BUFFER_MAX = int(os.getenv("RING_BUFFER_MAX", "10000"))
RISK_THRESHOLD = float(os.getenv("RISK_THRESHOLD", "0.80"))
WRITE_COALESCE = int(os.getenv("WRITE_COALESCE", "3"))


# Input Schema from Kafka topic 'transactions'
INPUT_SCHEMA = StructType(
    [
        StructField("transaction_id", StringType(), False),
        StructField("source_account", StringType(), True),
        StructField("dest_account", StringType(), True),
        StructField("trans_type", StringType(), True),
        StructField("amount", DoubleType(), True),
        StructField("old_balance_source", DoubleType(), True),
        StructField("new_balance_source", DoubleType(), True),
        StructField("old_balance_dest", DoubleType(), True),
        StructField("new_balance_dest", DoubleType(), True),
        StructField("channel", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("received_at", StringType(), True),
    ]
)


def update_state_and_extract_features(key, pdf_iter, state: GroupState):
    """
    Process sliding window state per source account backed by RocksDB.
    State has 6 fields:
      (account_id, last_known_balance, last_event_ts,
       recent_events_json, unique_dest_24h_json, hour_histogram_json)
    """
    if state.hasTimedOut:
        state.remove()
        return

    account_id = key[0]

    if state.exists:
        s = state.get
        state_dict = {
            "account_id": s[0],
            "last_known_balance": float(s[1] or 0.0),
            "last_event_ts": s[2],
            "recent_events": json.loads(s[3] or "[]"),
            "unique_dest_24h_json": s[4] or "{}",
            "hour_histogram_json": s[5] or "{}",
        }
    else:
        state_dict = {
            "account_id": account_id,
            "last_known_balance": 0.0,
            "last_event_ts": None,
            "recent_events": [],
            "unique_dest_24h_json": "{}",
            "hour_histogram_json": "{}",
        }

    outputs = []
    batch_seq = 0

    for pdf in pdf_iter:
        if pdf.empty:
            continue

        # Sort chronologically; tie-break by received_at for determinism
        sort_cols = [c for c in ["timestamp", "received_at"] if c in pdf.columns]
        if sort_cols:
            pdf = pdf.sort_values(sort_cols)

        # Dedup after sort — keeps deterministic "latest arrival"
        pdf = pdf.drop_duplicates(subset=["transaction_id"], keep="last")

        for _, row in pdf.iterrows():
            batch_seq += 1
            ev_ts = pd.Timestamp(row["timestamp"])
            amt = float(row.get("amount") or 0.0)

            # 1. Prune ring buffer + unique_dest (24h) + hour_histogram (30d)
            prune_and_sync_state(state_dict, ev_ts)

            # 2. Compute PIT features (pre-transaction view)
            feats = compute_features(state_dict, state_dict["recent_events"], row)

            # 3. Post-transaction snapshot for Silver (Section 2.7) using O(1) arithmetic
            post_c_30d = feats["_c_30d"] + 1
            post_s_30d = feats["_s_30d"] + amt
            post_s_sq_30d = feats["_s_sq_30d"] + (amt * amt)
            post_avg = float(post_s_30d / post_c_30d) if post_c_30d > 0 else 0.0
            if post_c_30d > 1:
                post_var = (post_s_sq_30d / post_c_30d) - (post_avg * post_avg)
                post_stddev = float(max(0.0, post_var) ** 0.5)
            else:
                post_stddev = 0.0

            # 4. Append to ring buffer (O(1) in-order, bisect for out-of-order)
            new_ev = {
                "ts": ev_ts.isoformat(),
                "amt": amt,
                "dst": str(row.get("dest_account") or ""),
            }
            events = state_dict["recent_events"]
            if not events or events[-1]["ts"] <= new_ev["ts"]:
                events.append(new_ev)
            else:
                import bisect

                idx = bisect.bisect_right(events, new_ev["ts"], key=lambda x: x["ts"])
                events.insert(idx, new_ev)

            # 5. Capacity overflow: slice-drop from head (no counters to desync)
            if len(events) > RING_BUFFER_MAX:
                overflow = len(events) - RING_BUFFER_MAX
                if overflow > RING_BUFFER_MAX * 0.1:
                    raise ValueError(
                        f"Account {account_id} ring buffer overflow {overflow} "
                        f"> 10% of RING_BUFFER_MAX={RING_BUFFER_MAX}. "
                        f"Feature accuracy for 30d window may be degraded."
                    )
                print(
                    f"[WARN] Account {account_id}: ring buffer overflow {overflow}, dropping oldest"
                )
                del events[:overflow]

            # 6. Update derived maps
            dest_acc = str(row.get("dest_account") or "")
            update_unique_dest(state_dict, dest_acc, ev_ts, max_tracked=200)
            update_hour_histogram(state_dict, ev_ts)

            state_dict["last_known_balance"] = float(
                row.get("new_balance_source") or 0.0
            )
            state_dict["last_event_ts"] = ev_ts.to_pydatetime()

            # Read back the current unique-dest count post-update for post-tx snapshot
            try:
                post_dests = json.loads(state_dict["unique_dest_24h_json"] or "{}")
            except Exception:
                post_dests = {}

            # 7. Emit output row
            outputs.append(
                {
                    "transaction_id": str(row["transaction_id"]),
                    "source_account": account_id,
                    "dest_account": dest_acc,
                    "trans_type": feats["trans_type"],
                    "channel": feats["channel"],
                    "timestamp": str(row.get("timestamp") or ""),
                    "received_at": str(row.get("received_at") or ""),
                    "old_balance_source": float(row.get("old_balance_source") or 0.0),
                    "new_balance_source": float(row.get("new_balance_source") or 0.0),
                    "old_balance_dest": float(row.get("old_balance_dest") or 0.0),
                    "new_balance_dest": float(row.get("new_balance_dest") or 0.0),
                    # Core numerics & log
                    "amount": feats["amount"],
                    "log_amount": feats["log_amount"],
                    # Balance dynamics & Remaining funds
                    "balance_drain_ratio": feats["balance_drain_ratio"],
                    "remaining_balance_ratio": feats["remaining_balance_ratio"],
                    "dest_to_source_bal_ratio": feats["dest_to_source_bal_ratio"],
                    "dest_is_merchant": feats["dest_is_merchant"],
                    "is_drain_attempt": feats["is_drain_attempt"],
                    "is_zero_dest_balance": feats["is_zero_dest_balance"],
                    "amount_to_old_balance_ratio": feats["amount_to_old_balance_ratio"],
                    # Card Testing & Micro & Structuring
                    "is_micro_transaction": feats["is_micro_transaction"],
                    "is_transfer_or_cashout": feats["is_transfer_or_cashout"],
                    # Window aggregates
                    "trans_count_1h": feats["trans_count_1h"],
                    "trans_count_24h": feats["trans_count_24h"],
                    "trans_count_7d": feats["trans_count_7d"],
                    "trans_count_1h_to_7d_ratio": feats["trans_count_1h_to_7d_ratio"],
                    "sum_amount_24h": feats["sum_amount_24h"],
                    "sum_amount_7d": feats["sum_amount_7d"],
                    "avg_amount_30d": feats["avg_amount_30d"],
                    "stddev_amount_30d": feats["stddev_amount_30d"],
                    "unique_dest_accounts_24h": feats["unique_dest_accounts_24h"],
                    "is_unusual_hour": feats["is_unusual_hour"],
                    # Ratios & Deviations
                    "amount_to_avg_ratio": feats["amount_to_avg_ratio"],
                    "amount_to_sum_7d_ratio": feats["amount_to_sum_7d_ratio"],
                    "amount_zscore_local": feats["amount_zscore_local"],
                    "amount_diff_avg_30d": feats["amount_diff_avg_30d"],
                    # Time-since-last & Velocity & Mule
                    "seconds_since_last_transaction": feats[
                        "seconds_since_last_transaction"
                    ],
                    "inbound_count_7d": feats["inbound_count_7d"],
                    "inbound_amount_7d": feats["inbound_amount_7d"],
                    "inbound_to_outbound_ratio_7d": feats[
                        "inbound_to_outbound_ratio_7d"
                    ],
                    "amount_to_dest_inbound_avg": feats["amount_to_dest_inbound_avg"],
                    "prev_transaction_amount": feats["prev_transaction_amount"],
                    "amount_ratio_to_prev": feats["amount_ratio_to_prev"],
                    "is_rapid_fire": feats["is_rapid_fire"],
                    "is_atm_cashout": feats["is_atm_cashout"],
                    # Cyclical
                    "hour_cos": feats["hour_cos"],
                    # Post-transaction snapshot
                    "post_tx_count_1h": int(feats["_c_1h"] + 1),
                    "post_tx_count_24h": int(feats["_c_24h"] + 1),
                    "post_tx_count_7d": int(feats["_c_7d"] + 1),
                    "post_sum_amount_24h": float(feats["_s_24h"] + amt),
                    "post_avg_amount_30d": post_avg,
                    "post_stddev_amount_30d": post_stddev,
                    "post_unique_dest_24h": int(len(post_dests)),
                    "frequent_tx_hours_json": json.dumps(feats["frequent_tx_hours"]),
                    "batch_seq": int(batch_seq),
                }
            )

    # Persist state (6 fields)
    state.update(
        (
            account_id,
            float(state_dict["last_known_balance"]),
            state_dict["last_event_ts"],
            json.dumps(state_dict["recent_events"]),
            state_dict["unique_dest_24h_json"],
            state_dict["hour_histogram_json"],
        )
    )
    STATE_TIMEOUT_MS = int(STATE_TIMEOUT_DAYS * 24 * 3600 * 1000)
    state.setTimeoutDuration(STATE_TIMEOUT_MS)

    if outputs:
        yield pd.DataFrame(outputs)


def run_detector():
    print("  STARTING STATEFUL FRAUD DETECTOR (applyInPandasWithState)       ")

    spark = (
        SparkSession.builder.appName("FraudDetection_Stateful_Detector")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.session.timeZone", "UTC")
        .config(
            "spark.sql.streaming.stateStore.providerClass",
            "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider",
        )
        .config("spark.sql.streaming.stateStore.rocksdb.blockCacheSizeMB", "128")
        .config("spark.sql.streaming.stateStore.rocksdb.writeBufferSizeMB", "32")
        .config("spark.sql.streaming.stateStore.rocksdb.compactOnCommit", "true")
        .config("spark.sql.streaming.stateStore.minDeltasForSnapshot", "10")
        .config("spark.hadoop.dfs.client-write-packet-size", "65536")
        .config("spark.sql.files.maxRecordsPerFile", "1000000")
        .config("spark.databricks.delta.optimizeWrite.enabled", "false")
        .config("spark.databricks.delta.autoCompact.enabled", "false")
        .config(
            "spark.executorEnv.PYTHONPATH",
            "/home/fraud/fraud_detection/spark_jobs/streaming",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    # Distribute Python helper modules to all remote cluster workers
    streaming_dir = os.path.dirname(os.path.abspath(__file__))
    for mod in ["feature_builder.py", "state_helpers.py", "model_loader.py"]:
        mod_path = os.path.join(streaming_dir, mod)
        if os.path.exists(mod_path):
            spark.sparkContext.addPyFile(mod_path)

    print("[INFO] Loading ML Pipeline Model on Driver...", flush=True)
    model = get_model(MODEL_PATH, CANDIDATE_PATH)

    print(
        f"[INFO] Subscribing to Kafka brokers {KAFKA_BROKERS}, topic '{KAFKA_TRANSACTION_TOPIC}'...",
        flush=True,
    )
    kafka_stream_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKERS)
        .option("subscribe", KAFKA_TRANSACTION_TOPIC)
        .option("startingOffsets", os.getenv("STARTING_OFFSETS", "earliest"))
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", os.getenv("MAX_OFFSETS_PER_TRIGGER", "2000"))
        .load()
    )

    parsed_stream_df = (
        kafka_stream_df.select(
            col("timestamp").alias("kafka_ts_raw"),
            col("value").cast("string").alias("json_payload"),
        )
        .select(
            col("kafka_ts_raw"),
            from_json(col("json_payload"), INPUT_SCHEMA).alias("data"),
        )
        .select("kafka_ts_raw", "data.*")
        .filter(col("transaction_id").isNotNull() & col("source_account").isNotNull())
        .withColumn("event_time", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))
        .withWatermark("event_time", "1 minute")
    )

    feature_stream_df = parsed_stream_df.groupBy(
        "source_account"
    ).applyInPandasWithState(
        func=update_state_and_extract_features,
        outputStructType=FEATURE_OUTPUT_SCHEMA,
        stateStructType=STATE_SCHEMA,
        outputMode="append",
        timeoutConf=GroupStateTimeout.ProcessingTimeTimeout,
    )

    scored_stream_df = model.transform(feature_stream_df)

    final_stream_df = (
        scored_stream_df.withColumn(
            "event_time", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
        )
        .withColumn("prob_array", vector_to_array(col("probability")))
        .withColumn("risk_score_raw", col("prob_array")[1].cast("double"))
        # Hybrid Rule Override: Prevent severe fraud attacks from being missed by ML threshold
        .withColumn(
            "is_critical_rule_flagged",
            ((col("balance_drain_ratio") >= 0.80) & (col("is_transfer_or_cashout") == 1.0))
            | ((col("is_rapid_fire") == 1.0) & (col("is_transfer_or_cashout") == 1.0))
            | ((col("amount_to_avg_ratio") >= 5.0) & (col("is_transfer_or_cashout") == 1.0))
            | ((col("amount_zscore_local") >= 3.0) & (col("is_transfer_or_cashout") == 1.0)),
        )
        .withColumn(
            "inspection_status",
            when(
                (col("risk_score_raw") >= RISK_THRESHOLD) | col("is_critical_rule_flagged"),
                lit("PENDING"),
            ).otherwise(lit("CLEARED")),
        )
        .withColumn(
            "risk_score",
            when(
                col("is_critical_rule_flagged") & (col("risk_score_raw") < lit(0.80)),
                lit(0.82),
            ).otherwise(col("risk_score_raw")),
        )
        .withColumn("model_version", lit("GBT_v1.0"))
        .withColumn("scored_at", current_timestamp())
        .withColumn(
            "latency_ms",
            when(
                coalesce(
                    to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss.SSS"),
                    to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss")
                ).isNotNull()
                & (
                    (unix_millis(current_timestamp()) - unix_millis(coalesce(
                        to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss.SSS"),
                        to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss")
                    ))) >= 0
                )
                & (
                    (unix_millis(current_timestamp()) - unix_millis(coalesce(
                        to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss.SSS"),
                        to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss")
                    ))) <= 86400000
                ),
                (unix_millis(current_timestamp()) - unix_millis(coalesce(
                    to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss.SSS"),
                    to_timestamp(col("received_at"), "yyyy-MM-dd HH:mm:ss")
                ))).cast("long")
            ).otherwise(
                (unix_millis(current_timestamp()) - unix_millis(col("event_time"))).cast("long")
            )
        )
        .withColumn(
            "raw_risk_factors",
            array(
                # 1. Dấu hiệu vét cạn tài khoản (rút số dư gốc)
                struct(
                    lit("balance_drain_ratio").alias("name"),
                    round(least(lit(1.0), col("balance_drain_ratio")), 4)
                    .cast("double")
                    .alias("contribution"),
                ),
                # 2. Đột biến số tiền so với trung bình 30 ngày (độ lệch chuẩn so với baseline)
                struct(
                    lit("amount_to_avg_ratio").alias("name"),
                    round(
                        least(
                            lit(1.0),
                            abs(col("amount_to_avg_ratio") - lit(1.0)) / lit(4.0),
                        ),
                        4,
                    )
                    .cast("double")
                    .alias("contribution"),
                ),
                # 3. Kênh giao dịch TRANSFER / CASH_OUT (kênh gian lận chính của PaySim)
                struct(
                    lit("is_transfer_or_cashout").alias("name"),
                    when(col("is_transfer_or_cashout") == 1.0, lit(0.35))
                    .otherwise(lit(0.0))
                    .cast("double")
                    .alias("contribution"),
                ),
                # 4. Giao dịch cấp tập liên tiếp (< 10 giây)
                struct(
                    lit("is_rapid_fire").alias("name"),
                    when(col("is_rapid_fire") == 1.0, lit(0.85))
                    .otherwise(lit(0.0))
                    .cast("double")
                    .alias("contribution"),
                ),
                # 5. Dấu hiệu thử thẻ / Micro card testing (<= 5.0)
                struct(
                    lit("card_testing_micro_tx").alias("name"),
                    when(col("is_micro_transaction") == 1.0, lit(0.60))
                    .otherwise(lit(0.0))
                    .cast("double")
                    .alias("contribution"),
                ),
                # 6. Độ lệch chuẩn bất thường z-score so với lịch sử khách hàng
                struct(
                    lit("amount_zscore_anomaly").alias("name"),
                    round(
                        least(lit(1.0), abs(col("amount_zscore_local")) / lit(5.0)),
                        4,
                    )
                    .cast("double")
                    .alias("contribution"),
                ),
                # 7. Khung giờ bất thường so với thói quen 30 ngày
                struct(
                    lit("is_unusual_hour").alias("name"),
                    when(col("is_unusual_hour") == 1.0, lit(0.40))
                    .otherwise(lit(0.0))
                    .cast("double")
                    .alias("contribution"),
                ),
                # 8. Tần suất giao dịch tăng vọt trong 1 giờ
                struct(
                    lit("velocity_1h_spike").alias("name"),
                    round(least(lit(1.0), col("trans_count_1h") / lit(10.0)), 4)
                    .cast("double")
                    .alias("contribution"),
                ),
            ),
        )
        .withColumn(
            "top_risk_factors",
            expr(
                "slice(array_sort(raw_risk_factors, "
                "(left, right) -> case when left.contribution < right.contribution then 1 "
                "when left.contribution > right.contribution then -1 else 0 end), 1, 3)"
            ),
        )
        .drop("raw_risk_factors", "is_critical_rule_flagged", "risk_score_raw")
    )

    def write_sinks(micro_batch_df, batch_id):
        if micro_batch_df.isEmpty():
            return

        micro_batch_df.cache()
        metrics_row = micro_batch_df.select(
            spark_count(lit(1)).alias("total_count"),
            spark_count(when(col("inspection_status") == "PENDING", lit(1))).alias("fraud_count"),
            spark_avg("latency_ms").alias("avg_latency"),
            expr("percentile_approx(latency_ms, 0.99)").alias("p99_latency"),
        ).collect()[0]

        batch_count = int(metrics_row["total_count"] or 0)
        fraud_count = int(metrics_row["fraud_count"] or 0)
        avg_lat = float(metrics_row["avg_latency"] or 0.0)
        p99_lat = float(metrics_row["p99_latency"] or 0.0)

        print(
            f"\n--- [Stateful Batch {batch_id}] Scored {batch_count} records | Alerts: {fraud_count} | Latency: avg={avg_lat:.1f}ms, P99={p99_lat:.1f}ms ---",
            flush=True,
        )

        t_batch_start = time.time()
        try:
            # SINK 1 (CRITICAL PATH): Kafka alerts first
            if fraud_count > 0:
                alerts_df = micro_batch_df.filter(
                    col("inspection_status") == "PENDING"
                ).select(
                    col("transaction_id").alias("key"),
                    to_json(
                        struct(
                            col("transaction_id"),
                            col("source_account"),
                            col("dest_account"),
                            col("trans_type"),
                            col("amount"),
                            col("channel"),
                            col("timestamp").cast("string").alias("timestamp"),
                            col("received_at"),
                            col("risk_score"),
                            lit(1).alias("prediction_label"),
                            col("inspection_status"),
                            col("model_version"),
                            col("latency_ms"),
                            col("top_risk_factors"),
                        )
                    ).alias("value"),
                )

                alerts_df.coalesce(1).write.format("kafka").option(
                    "kafka.bootstrap.servers", KAFKA_BROKERS
                ).option("topic", KAFKA_ALERTS_TOPIC).option(
                    "kafka.enable.idempotence", "true"
                ).option(
                    "kafka.acks", "all"
                ).save()
                print(
                    f"Batch {batch_id}: Emitted {fraud_count} alerts to Kafka topic '{KAFKA_ALERTS_TOPIC}' (Immediate Alerting Path)",
                    flush=True,
                )

            t_alert_done = time.time()
            alerting_time_ms = (t_alert_done - t_batch_start) * 1000.0

            # SINK 2 (PERSISTENCE): Gold Delta append (idempotent via txnAppId+txnVersion, coalesce(WRITE_COALESCE), NO mergeSchema)
            gold_df = micro_batch_df.select(
                "transaction_id",
                "source_account",
                "dest_account",
                "trans_type",
                "amount",
                "channel",
                col("event_time").alias("timestamp"),
                "received_at",
                "old_balance_source",
                "old_balance_dest",
                "risk_score",
                "inspection_status",
                "model_version",
                "latency_ms",
                "top_risk_factors",
                "scored_at",
            )
            t_persist_start = time.time()
            gold_df.coalesce(WRITE_COALESCE).write.format("delta").mode("append").option(
                "txnAppId", TXN_APP_ID
            ).option("txnVersion", batch_id).save(GOLD_RISK_SCORES)
            t_persist_done = time.time()
            persist_time_ms = (t_persist_done - t_persist_start) * 1000.0

            print(
                f"Batch {batch_id}: [PERSIST DONE] Appended {batch_count} records to Gold ({persist_time_ms:.1f}ms) | Alerting: {alerting_time_ms:.1f}ms",
                flush=True,
            )

        finally:
            micro_batch_df.unpersist()

    print(
        f"[INFO] Starting Stateful Streaming Query with Checkpoint at {CHECKPOINT_PATH}...",
        flush=True,
    )
    query = (
        final_stream_df.writeStream.queryName("Fraud_Detector_Stateful")
        .option("checkpointLocation", CHECKPOINT_PATH)
        .trigger(processingTime="2 second")
        .foreachBatch(write_sinks)
        .start()
    )

    print("[INFO] Streaming Query is ACTIVE and waiting for data...", flush=True)
    query.awaitTermination()


if __name__ == "__main__":
    run_detector()
