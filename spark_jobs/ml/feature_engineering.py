import os
import math
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import (
    col,
    count,
    sum as spark_sum,
    round as spark_round,
    coalesce,
    lit,
    when,
    current_timestamp,
    hour,
    array_contains,
    collect_set,
    size,
    expr,
    cos as spark_cos,
    lag as spark_lag,
    greatest as spark_greatest,
)
from delta.tables import DeltaTable


from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

# Config
SILVER_TRANSACTIONS = os.getenv("SILVER_TRANSACTIONS", "hdfs:///lakehouse/fraud_detection/silver/transactions")
SILVER_DECISIONS    = os.getenv("SILVER_DECISIONS", "hdfs:///lakehouse/fraud_detection/silver/inspection_decisions")
FEATURES            = os.getenv("FEATURES", "hdfs:///lakehouse/fraud_detection/features")
CSV_FILE_PATH       = os.getenv("CSV_FILE_PATH", "file:///home/fraud/synthetic_transactions.csv")

COCKROACH_HOST      = os.getenv("COCKROACH_HOST", "192.168.80.201")
COCKROACH_PORT      = os.getenv("COCKROACH_PORT", "26257")
COCKROACH_DB        = os.getenv("COCKROACH_DB", "system_db")
COCKROACH_USER      = os.getenv("COCKROACH_USER", "admin")
COCKROACH_PASSWORD  = os.getenv("COCKROACH_PASSWORD", "admin123")
COCKROACH_JDBC_URL  = os.getenv("COCKROACH_JDBC_URL", f"jdbc:postgresql://{COCKROACH_HOST}:{COCKROACH_PORT}/{COCKROACH_DB}?sslmode=disable")


spark = (
    SparkSession.builder
    .appName("PIT_FeatureStore")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.debug.maxToStringFields", "200")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.shuffle.partitions", "36")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# 1. Read Silver Transactions
print("Reading Silver Transactions layer...")
tx_raw = spark.read.format("delta").load(SILVER_TRANSACTIONS)

needed_cols = [
    "transaction_id", "source_account", "dest_account", "trans_type",
    "amount", "old_balance_source", "old_balance_dest",
    "channel", "timestamp", "partition_date",
]
tx_df = tx_raw.select([col(c) for c in needed_cols if c in tx_raw.columns])

if "channel" not in tx_df.columns:
    tx_df = tx_df.withColumn("channel", lit("UNKNOWN"))

# 2. Merge CSV Ground Truth Labels
csv_join_ok = False
try:
    print(f"Loading ground truth labels from CSV: {CSV_FILE_PATH}...")
    csv_raw = spark.read.option("header", "true").csv(CSV_FILE_PATH)

    has_tx_id = "transaction_id" in csv_raw.columns
    print(f"[CSV] Detected 'transaction_id' column: {has_tx_id}")

    if has_tx_id:
        csv_labels_df = (
            csv_raw.select(
                col("transaction_id").alias("csv_tx_id"),
                col("isFraud").cast("int").alias("csv_ground_truth"),
            )
            .filter(col("csv_tx_id").isNotNull())
            .dropDuplicates(["csv_tx_id"])
        )
        tx_df = tx_df.join(
            csv_labels_df,
            tx_df.transaction_id == csv_labels_df.csv_tx_id,
            "left",
        ).drop("csv_tx_id")
    else:
        csv_labels_df = csv_raw.select(
            col("nameOrig").alias("c_source"),
            col("nameDest").alias("c_dest"),
            col("type").alias("c_type"),
            spark_round(col("amount").cast("double"), 2).alias("c_amount"),
            spark_round(col("oldbalanceOrg").cast("double"), 2).alias("c_old_source"),
            col("isFraud").cast("int").alias("csv_ground_truth"),
        ).dropDuplicates(["c_source", "c_dest", "c_type", "c_amount", "c_old_source"])

        tx_df = tx_df.join(
            csv_labels_df,
            (tx_df.source_account == csv_labels_df.c_source)
            & (tx_df.dest_account == csv_labels_df.c_dest)
            & (tx_df.trans_type == csv_labels_df.c_type)
            & (spark_round(tx_df.amount, 2) == csv_labels_df.c_amount)
            & (spark_round(tx_df.old_balance_source, 2) == csv_labels_df.c_old_source),
            "left",
        ).drop("c_source", "c_dest", "c_type", "c_amount", "c_old_source")

    csv_join_ok = True

except Exception as e:
    print(f"[WARN] Could not read CSV labels: {e}")
    tx_df = tx_df.withColumn("csv_ground_truth", lit(0).cast("int"))

if csv_join_ok:
    total_silver = tx_df.count()
    matched = tx_df.filter(col("csv_ground_truth").isNotNull()).count()
    match_rate = 100.0 * matched / total_silver if total_silver > 0 else 0.0
    print(f"[VERIFY] CSV join match: {matched:,}/{total_silver:,} = {match_rate:.2f}%")


# 3. Merge Auditor Labels (Delta + CockroachDB feedback loop)
auditor_labels_df = None

if DeltaTable.isDeltaTable(spark, SILVER_DECISIONS):
    print(f"Loading auditor feedback labels from {SILVER_DECISIONS}...")
    auditor_delta_df = spark.read.format("delta").load(SILVER_DECISIONS)

    cand_label_col = None
    for cand in ["inspection_label", "decision_label", "nhan", "label"]:
        if cand in auditor_delta_df.columns:
            cand_label_col = cand
            break

    if cand_label_col:
        auditor_labels_df = (
            auditor_delta_df.select(
                col("transaction_id").alias("auditor_tx_id"),
                col(cand_label_col).cast("int").alias("auditor_label"),
            )
            .filter(col("auditor_label").isNotNull())
            .dropDuplicates(["auditor_tx_id"])
        )

try:
    db_reviewed = (
        spark.read.format("jdbc")
        .option("url", COCKROACH_JDBC_URL)
        .option(
            "dbtable",
            "(SELECT transaction_id, decision_label, inspector_id, reason, updated_at "
            "FROM transactions WHERE decision_label IS NOT NULL) AS reviewed_tx",
        )
        .option("user", COCKROACH_USER)
        .option("password", COCKROACH_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .load()
    )

    db_count = db_reviewed.count()
    if db_count > 0:
        print(f"Found {db_count} reviewed verdicts in CockroachDB serving store.")
        db_labels = db_reviewed.select(
            col("transaction_id").alias("auditor_tx_id"),
            col("decision_label").cast("int").alias("auditor_label"),
        ).dropDuplicates(["auditor_tx_id"])

        if auditor_labels_df is not None:
            auditor_labels_df = auditor_labels_df.union(db_labels).dropDuplicates(["auditor_tx_id"])
        else:
            auditor_labels_df = db_labels

        try:
            db_sync_df = db_reviewed.select(
                col("transaction_id"),
                col("decision_label").cast("int").alias("inspection_label"),
                col("inspector_id").cast("string").alias("inspector_id"),
                lit("AUDITOR_WEB").alias("label_source"),
                col("updated_at").alias("inspected_at"),
                col("reason"),
                lit(5).alias("handling_time_seconds"),
            )
            db_sync_df.write.format("delta").mode("append") \
                .option("mergeSchema", "true").save(SILVER_DECISIONS)
            print(f"Synced {db_count} verdicts to {SILVER_DECISIONS}.")
        except Exception as e_sync:
            print(f"[Notice] Sync to silver decisions Delta: {e_sync}")

except Exception as e_crdb:
    print(f"[Notice] CockroachDB reviewed lookup failed: {e_crdb}")

if auditor_labels_df is not None and auditor_labels_df.count() > 0:
    print("Applying auditor feedback labels onto transactions...")
    tx_df = (
        tx_df.join(
            auditor_labels_df,
            tx_df.transaction_id == auditor_labels_df.auditor_tx_id,
            "left",
        )
        .withColumn(
            "is_fraud_label",
            coalesce(col("auditor_label"), col("csv_ground_truth"), lit(0)).cast("int"),
        )
        .drop("auditor_tx_id", "auditor_label", "csv_ground_truth")
    )
else:
    print("No auditor labels found. Using CSV ground truth as is_fraud_label.")
    tx_df = tx_df.withColumn(
        "is_fraud_label",
        coalesce(col("csv_ground_truth"), lit(0)).cast("int"),
    ).drop("csv_ground_truth")

print("Labels resolved (Priority: Auditor > CSV > Default 0).")


# 4. Windows
print("Configuring PIT & Sliding Window functions...")
tx_df = tx_df \
    .withColumn("timestamp", col("timestamp").cast("timestamp")) \
    .withColumn("ts_sec", col("timestamp").cast("long"))

# Source-side windows
w_1h  = Window.partitionBy("source_account").orderBy("ts_sec").rangeBetween(-3600, -1)
w_7d  = Window.partitionBy("source_account").orderBy("ts_sec").rangeBetween(-7 * 86400, -1)
w_30d = Window.partitionBy("source_account").orderBy("ts_sec").rangeBetween(-30 * 86400, -1)

# Previous-row window
w_prev_transaction = (
    Window.partitionBy("source_account").orderBy("ts_sec").rowsBetween(-1, -1)
)

# Destination-side window (mule fan-in)
w_inbound_7d = Window.partitionBy("dest_account").orderBy("ts_sec").rangeBetween(-7 * 86400, -1)


# 5. Base features
tx_with_base_features = (
    tx_df
    .withColumn("trans_count_1h",  coalesce(count("transaction_id").over(w_1h), lit(0)))
    .withColumn("trans_count_7d",  coalesce(count("transaction_id").over(w_7d), lit(0)))
    .withColumn("trans_count_30d", coalesce(count("transaction_id").over(w_30d), lit(0)))
    .withColumn("sum_amount_7d",   coalesce(spark_sum("amount").over(w_7d), lit(0.0)))
    .withColumn("sum_amount_30d",  coalesce(spark_sum("amount").over(w_30d), lit(0.0)))
    .withColumn("sum_amount_sq_30d",
                coalesce(spark_sum(col("amount") * col("amount")).over(w_30d), lit(0.0)))
    .withColumn("habitual_hours_30d",
                collect_set(hour("timestamp")).over(w_30d))
    .withColumn("last_transaction_ts_sec",
                spark_lag("ts_sec").over(w_prev_transaction))
    .withColumn("prev_transaction_amount",
                spark_lag("amount").over(w_prev_transaction))
    .withColumn("inbound_count_7d",
                coalesce(count("transaction_id").over(w_inbound_7d), lit(0)))
    .withColumn("inbound_amount_7d",
                coalesce(spark_sum("amount").over(w_inbound_7d), lit(0.0)))
)

# 6. Final feature projection
feature_store_df = (
    tx_with_base_features

    # ---- Basic aggregates ----
    .withColumn("avg_amount_30d",
        when(col("trans_count_30d") > 0,
             col("sum_amount_30d") / col("trans_count_30d"))
        .otherwise(lit(0.0)))
    .withColumn("is_unusual_hour",
        when(col("trans_count_30d") > 0,
             when(array_contains(col("habitual_hours_30d"), hour("timestamp")),
                  lit(0.0)).otherwise(lit(1.0)))
        .otherwise(lit(0.0)))

    # ---- Non-linear Amount & Differences ----
    .withColumn("log_amount",
        spark_round(expr("ln(greatest(amount, 0.0) + 1.0)"), 4))
    .withColumn("amount_diff_avg_30d",
        spark_round(col("amount") - col("avg_amount_30d"), 4))

    # ---- Balance dynamics & Remaining funds ----
    .withColumn("balance_drain_ratio",
        when(col("old_balance_source") > 0,
             spark_round(spark_greatest(lit(0.0), col("amount") / col("old_balance_source")), 4))
        .otherwise(lit(1.0)))
    .withColumn("remaining_balance_ratio",
        when(col("old_balance_source") > 0,
             spark_round(spark_greatest(lit(0.0), col("old_balance_source") - col("amount")) / col("old_balance_source"), 4))
        .otherwise(lit(0.0)))
    .withColumn("dest_to_source_bal_ratio",
        spark_round(col("old_balance_dest") / (col("old_balance_source") + 1.0), 4))
    .withColumn("dest_is_merchant",
        when(col("dest_account").startswith("M"), lit(1.0)).otherwise(lit(0.0)))

    # ---- High-risk Type & AML Structuring ----
    .withColumn("is_transfer_or_cashout",
        when(col("trans_type").isin(["TRANSFER", "CASH_OUT"]), lit(1.0)).otherwise(lit(0.0)))

    # ---- Card testing & Micro-transactions ----
    .withColumn("is_micro_transaction",
        when(col("amount") <= 5.0, lit(1.0)).otherwise(lit(0.0)))

    # ---- Ratios & Deviations ----
    .withColumn("amount_to_avg_ratio",
        when(col("avg_amount_30d") > 0,
             col("amount") / col("avg_amount_30d"))
        .otherwise(lit(1.0)))
    .withColumn("amount_to_sum_7d_ratio",
        when(col("sum_amount_7d") > 0,
             spark_round(col("amount") / (col("sum_amount_7d") + 1.0), 4))
        .otherwise(lit(1.0)))

    # ---- Amount z-score ----
    .withColumn("amount_zscore_local",
        when((col("trans_count_30d") > 1)
             & (col("sum_amount_sq_30d") > 0),
             spark_round(
                 (col("amount") - col("avg_amount_30d")) /
                 spark_greatest(
                     spark_round(expr(
                         "sqrt(greatest(0.0, "
                         "(sum_amount_sq_30d / trans_count_30d) - "
                         "(avg_amount_30d * avg_amount_30d)))"), 4),
                     lit(1.0)),
                 4))
        .otherwise(lit(0.0)))

    # ---- Time since last ----
    .withColumn("seconds_since_last_transaction",
        when(col("last_transaction_ts_sec").isNotNull(),
             col("ts_sec") - col("last_transaction_ts_sec"))
        .otherwise(lit(-1)))

    # ---- VELOCITY-specific ----
    .withColumn("amount_ratio_to_prev",
        when((col("prev_transaction_amount").isNotNull())
             & (col("prev_transaction_amount") > 0),
             spark_round(col("amount") / col("prev_transaction_amount"), 4))
        .otherwise(lit(1.0)))
    .withColumn("is_rapid_fire",
        when((col("seconds_since_last_transaction") >= 0)
             & (col("seconds_since_last_transaction") < 10),
             lit(1.0))
        .otherwise(lit(0.0)))
    .withColumn("trans_count_1h_to_7d_ratio",
        spark_round(col("trans_count_1h") / (col("trans_count_7d") + 1.0), 4))

    # ---- Destination & Mule Inbound flow ----
    .withColumn("inbound_to_outbound_ratio_7d",
        when(col("sum_amount_7d") > 0,
             spark_round(col("inbound_amount_7d") / (col("sum_amount_7d") + 1.0), 4))
        .otherwise(lit(0.0)))
    .withColumn("amount_to_dest_inbound_avg",
        when(col("inbound_count_7d") > 0,
             spark_round(col("amount") / ((col("inbound_amount_7d") / col("inbound_count_7d")) + 1.0), 4))
        .otherwise(lit(1.0)))

    # ---- ATM Cash-out Laundering ----
    .withColumn("is_atm_cashout",
        when((col("trans_type") == "CASH_OUT") & (col("channel") == "ATM"), lit(1.0))
        .otherwise(lit(0.0)))

    # ---- Cyclical hour ----
    .withColumn("hour_cos",
        spark_round(spark_cos(col("ts_sec").cast("double") * 2.0 * math.pi / 86400.0), 6))

    # ---- FIX: fill NULL prev_transaction_amount with sentinel -1 ----
    .withColumn("prev_transaction_amount",
        when(col("prev_transaction_amount").isNotNull(),
             col("prev_transaction_amount"))
        .otherwise(lit(-1.0)))

    .select(
        # identifiers / pass-through
        col("transaction_id"),
        col("source_account"),
        col("dest_account"),
        col("trans_type"),
        col("channel"),
        col("is_fraud_label"),
        col("timestamp"),
        col("partition_date"),

        # Core numerics & log
        col("amount"),
        col("log_amount"),
        col("old_balance_source"),
        col("old_balance_dest"),

        # Balance dynamics & Remaining funds
        col("balance_drain_ratio"),
        col("remaining_balance_ratio"),
        col("dest_to_source_bal_ratio"),
        col("dest_is_merchant"),

        # Card Testing & Micro & Structuring
        col("is_micro_transaction"),
        col("is_transfer_or_cashout"),

        # Window aggregates
        col("trans_count_1h"),
        col("trans_count_7d"),
        col("trans_count_1h_to_7d_ratio"),
        col("avg_amount_30d"),
        col("is_unusual_hour"),

        # Ratios & Deviations
        col("amount_to_avg_ratio"),
        col("amount_to_sum_7d_ratio"),
        col("amount_zscore_local"),
        col("amount_diff_avg_30d"),

        # Time-since-last & Velocity & Mule
        col("seconds_since_last_transaction"),
        col("inbound_count_7d"),
        col("inbound_amount_7d"),
        col("inbound_to_outbound_ratio_7d"),
        col("amount_to_dest_inbound_avg"),
        col("prev_transaction_amount"),
        col("amount_ratio_to_prev"),
        col("is_rapid_fire"),
        col("is_atm_cashout"),

        # Cyclical
        col("hour_cos"),
    )
)

# 7. Sanitize: fill any remaining NULLs in numeric columns (belt & suspenders)
PASSTHROUGH_COLS = {
    "transaction_id", "source_account", "dest_account",
    "trans_type", "channel", "timestamp", "partition_date",
    "is_fraud_label",
}
numeric_cols = [c for c in feature_store_df.columns if c not in PASSTHROUGH_COLS]

print(f"[SANITIZE] Filling NULLs in {len(numeric_cols)} numeric columns...")
feature_store_df = feature_store_df.fillna({c: 0.0 for c in numeric_cols})


# 8. Save
print(f"Saving Point-in-Time Feature Store to HDFS: {FEATURES}")
feature_store_df.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .option("delta.enableChangeDataFeed", "true") \
    .save(FEATURES)

print("Point-in-Time Feature Dataset v6 built successfully.")
spark.stop()