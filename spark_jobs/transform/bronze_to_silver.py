import os
import sys
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, sum as spark_sum, current_timestamp,
    when, expr, row_number, to_timestamp, lit, coalesce,
    concat_ws, greatest, current_date
)
from pyspark.sql.window import Window
from delta.tables import DeltaTable

spark = (
    SparkSession.builder.appName("FraudDetection_BronzeToSilver")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

BRONZE_PATH         = os.getenv("BRONZE_PATH", "hdfs:///lakehouse/fraud_detection/bronze")
SILVER_TRANSACTIONS = os.getenv("SILVER_TRANSACTIONS", "hdfs:///lakehouse/fraud_detection/silver/transactions")
QUARANTINE_PATH     = os.getenv("QUARANTINE_PATH", "hdfs:///lakehouse/fraud_detection/_quarantine")
AUDIT_STATS_PATH    = os.getenv("AUDIT_STATS_PATH") or os.getenv("SILVER_AUDIT_STATS", "hdfs:///lakehouse/fraud_detection/silver/_audit_stats")


REQUIRED_BRONZE_COLS = {
    "timestamp",
    "transaction_id",
    "source_account",
    "dest_account",
    "amount",
    "trans_type",
}

target_date = None
full_mode = False

if "--full" in sys.argv:
    full_mode = True

for flag in ["--date"]:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            target_date = sys.argv[idx + 1]
            break

# Nếu không có --date và không có --full → mặc định = hôm nay
if target_date is None and not full_mode:
    target_date = datetime.now().strftime("%Y-%m-%d")

# 1. Read Bronze Delta Table
bronze_raw = spark.read.format("delta").load(BRONZE_PATH)

missing = REQUIRED_BRONZE_COLS - set(bronze_raw.columns)
if missing:
    raise ValueError(f"Bronze schema drift — missing columns: {sorted(missing)}")

if "partition_date" not in bronze_raw.columns:
    raise ValueError(
        "Bronze has no partition_date column — cannot filter by partition_date"
    )

if full_mode:
    print("--- READING FULL BRONZE DELTA LAKE (all dates) ---")
    bronze_df = bronze_raw
else:
    print(f"--- FILTERING BRONZE FOR PARTITION DATE: {target_date} ---")
    bronze_df = bronze_raw.filter(col("partition_date") == target_date)


def pick_ingest_col(df):
    if "_ingest_ts" in df.columns:
        return col("_ingest_ts")
    if "received_at" in df.columns:
        return coalesce(to_timestamp(col("received_at")), current_timestamp())
    return current_timestamp()


ingest_col = pick_ingest_col(bronze_df)
EXCLUSION_RULES = ["r1_null_fields", "r2_invalid_amount", "r3_future_ts"]

# 2. Quality Evaluation with Audit Flags
flagged_df = (
    bronze_df.withColumn(
        "_event_ts", coalesce(to_timestamp(col("timestamp")), current_timestamp())
    )
    .withColumn("_ingest_ts", ingest_col)
    .withColumn(
        "partition_date",
        coalesce(
            col("partition_date").cast("date"),
            col("_event_ts").cast("date"),
            current_date(),
        ).cast("string"),
    )
    .withColumn(
        "r1_null_fields",
        col("transaction_id").isNull()
        | col("source_account").isNull()
        | col("dest_account").isNull(),
    )
    .withColumn("r2_invalid_amount", col("amount").isNull() | (col("amount") <= 0))
    .withColumn(
        "r3_future_ts",
        col("_event_ts") > (current_timestamp() + expr("INTERVAL 1 DAY")),
    )
    .withColumn(
        "is_quarantined",
        greatest(*[col(rule).cast("int") for rule in EXCLUSION_RULES]) == 1,
    )
)

flagged_df.cache()

# 3. Branch A: Data Quality Audit Statistics Table
batch_date_val = target_date if target_date else "FULL_LOAD"

audit_stats_df = (
    flagged_df.agg(
        count("*").alias("total_input"),
        *[spark_sum(col(rule).cast("int")).alias(rule) for rule in EXCLUSION_RULES],
        spark_sum(col("is_quarantined").cast("int")).alias("total_quarantined"),
    )
    .withColumn("batch_date", lit(batch_date_val))
    .withColumn("audit_timestamp", current_timestamp())
)

print("=== DATA QUALITY AUDIT STATISTICS ===")
audit_stats_row = audit_stats_df.first()
audit_stats_df.show(truncate=False)

total_input = audit_stats_row["total_input"] or 0
total_quarantined = audit_stats_row["total_quarantined"] or 0
total_valid = total_input - total_quarantined

# Idempotent write
audit_writer = audit_stats_df.write.format("delta").option("mergeSchema", "true")
if target_date and DeltaTable.isDeltaTable(spark, AUDIT_STATS_PATH):
    audit_writer.mode("overwrite").option(
        "replaceWhere", f"batch_date = '{target_date}'"
    ).save(AUDIT_STATS_PATH)
else:
    print(f"--- APPENDING to audit stats (batch_date = {batch_date_val}) ---")
    audit_writer.mode("append").save(AUDIT_STATS_PATH)

# 4. Branch B: Quarantine Storage with Reason
if total_quarantined > 0:
    quarantine_df = (
        flagged_df.filter(col("is_quarantined"))
        .withColumn(
            "quarantine_reason",
            concat_ws(",", *[when(col(rule), lit(rule)) for rule in EXCLUSION_RULES]),
        )
        .withColumn("quarantined_at", current_timestamp())
    )

    q_writer = (
        quarantine_df.write.format("delta")
        .partitionBy("partition_date")
        .option("mergeSchema", "true")
    )
    if target_date and DeltaTable.isDeltaTable(spark, QUARANTINE_PATH):
        q_writer.mode("overwrite").option(
            "replaceWhere", f"partition_date = '{target_date}'"
        ).save(QUARANTINE_PATH)
    else:
        q_writer.mode("append").save(QUARANTINE_PATH)

# 5. Branch C: Clean Silver Ingestion & Dedup
if total_valid > 0:
    raw_valid_df = flagged_df.filter(~col("is_quarantined")).drop(
        *EXCLUSION_RULES, "is_quarantined"
    )

    # 6. Deduplication (Deterministic: pick newest _ingest_ts per transaction_id)
    window_dedup = Window.partitionBy("transaction_id").orderBy(col("_ingest_ts").desc())
    valid_df = (
        raw_valid_df.withColumn("_row_num", row_number().over(window_dedup))
        .filter(col("_row_num") == 1)
        .drop("_row_num")
        .dropDuplicates(["source_account", "dest_account", "amount", "trans_type", "_event_ts"])
    )

    # 7. Merge Clean Records into Silver Transactions Table
    if DeltaTable.isDeltaTable(spark, SILVER_TRANSACTIONS):
        if target_date:
            # Per-day run: static partition pruning
            merge_condition = (
                f"t.partition_date = '{target_date}' AND "
                f"t.partition_date = s.partition_date AND "
                f"t.transaction_id = s.transaction_id"
            )
        else:
            # Full run: dynamic partition pruning
            merge_condition = (
                "t.partition_date = s.partition_date AND "
                "t.transaction_id = s.transaction_id"
            )
        print(
            f"--- MERGING INTO SILVER TRANSACTIONS (Condition: {merge_condition}) ---"
        )
        DeltaTable.forPath(spark, SILVER_TRANSACTIONS).alias("t").merge(
            valid_df.alias("s"), merge_condition
        ).whenMatchedUpdateAll(
            condition="s._ingest_ts > t._ingest_ts"
        ).whenNotMatchedInsertAll().execute()
    else:
        print("--- INITIAL WRITE TO SILVER TRANSACTIONS (OVERWRITE) ---")
        valid_df.write.format("delta").mode("overwrite").partitionBy(
            "partition_date"
        ).option("overwriteSchema", "true").save(SILVER_TRANSACTIONS)
else:
    print("--- No valid records to merge into Silver Transactions ---")

flagged_df.unpersist()
flagged_df = None

print("--- BRONZE TO SILVER PIPELINE COMPLETED SUCCESSFULLY ---")
spark.stop()