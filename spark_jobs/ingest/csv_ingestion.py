import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, current_timestamp, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, DateType
)

# Spark session (giống Kafka version)

print("--- INITIALIZING SPARK BATCH (CSV BACKFILL MODE) ---")

spark = SparkSession.builder \
    .appName("FraudDetection_BronzeIngestCSV") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.databricks.delta.optimizeWrite.enabled", "true") \
    .config("spark.databricks.delta.autoCompact.enabled", "true") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Suppress Netty transport shutdown noise
try:
    log4j = spark._jvm.org.apache.log4j
    for noisy in [
        "org.apache.spark.network.client.TransportResponseHandler",
        "org.apache.spark.network.server.TransportChannelHandler",
        "org.apache.spark.ContextCleaner",
    ]:
        log4j.Logger.getLogger(noisy).setLevel(log4j.Level.OFF)
except Exception:
    pass

# CSV raw schema — chỉ khai báo cột MÌNH CẦN

csv_schema = StructType([
    StructField("step",             IntegerType(), True),
    StructField("transaction_id",   StringType(),  False),
    StructField("timestamp",        StringType(),  True),
    StructField("type",             StringType(),  True),
    StructField("amount",           DoubleType(),  True),
    StructField("nameOrig",         StringType(),  True),
    StructField("oldbalanceOrg",    DoubleType(),  True),
    StructField("newbalanceOrig",   DoubleType(),  True),
    StructField("nameDest",         StringType(),  True),
    StructField("oldbalanceDest",   DoubleType(),  True),
    StructField("newbalanceDest",   DoubleType(),  True),
    StructField("channel",          StringType(),  True),
])

# Configuration (giống style Kafka version)

INPUT_CSV     = os.getenv("INPUT_CSV", "file:///home/fraud/synthetic_transactions.csv")
BRONZE_PATH   = os.getenv("BRONZE_PATH", "/lakehouse/fraud_detection/bronze")
WRITE_MODE    = os.getenv("WRITE_MODE", "append").lower()
CSV_HAS_HEADER = os.getenv("CSV_HAS_HEADER", "true").lower() == "true"

print(f"--- INPUT CSV:      {INPUT_CSV} ---")
print(f"--- BRONZE PATH:    {BRONZE_PATH} ---")
print(f"--- WRITE MODE:     {WRITE_MODE} ---")
print(f"--- CSV HAS HEADER: {CSV_HAS_HEADER} ---")

# Read CSV (batch)

print("--- READING CSV ---")

raw_df = spark.read \
    .format("csv") \
    .option("header", str(CSV_HAS_HEADER).lower()) \
    .option("mode", "PERMISSIVE") \
    .option("multiLine", "false") \
    .schema(csv_schema) \
    .load(INPUT_CSV)

# Map sang schema Bronze + enrich metadata

print("--- MAPPING TO BRONZE SCHEMA ---")

bronze_df = raw_df.select(
    col("transaction_id").alias("transaction_id"),
    col("nameOrig").alias("source_account"),
    col("nameDest").alias("dest_account"),
    col("type").alias("trans_type"),
    col("amount").alias("amount"),
    col("oldbalanceOrg").alias("old_balance_source"),
    col("newbalanceOrig").alias("new_balance_source"),
    col("oldbalanceDest").alias("old_balance_dest"),
    col("newbalanceDest").alias("new_balance_dest"),
    col("channel").alias("channel"),
    col("timestamp").alias("timestamp"),
    col("timestamp").alias("received_at"),
)

bronze_df = bronze_df \
    .withColumn("_ingest_ts", current_timestamp()) \
    .withColumn("_source", lit("csv")) \
    .withColumn("_schema_ver", lit("v1.0")) \
    .withColumn(
        "_event_time",
        to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"),
    ) \
    .withColumn(
        "partition_date",
        col("_event_time").cast(DateType()),
    ) \

# Sanity: filter rows có timestamp không parse được

bad_ts_df = bronze_df.filter(col("partition_date").isNull())
bad_ts_count = bad_ts_df.count()
if bad_ts_count > 0:
    print(f"--- WARNING: {bad_ts_count:,} rows dropped (invalid timestamp) ---")
    bronze_df = bronze_df.filter(col("partition_date").isNotNull())

# Write Bronze Delta

print(f"--- WRITING BRONZE DELTA: {BRONZE_PATH} (mode={WRITE_MODE}) ---")

write_mode = "overwrite" if WRITE_MODE == "overwrite" else "append"

bronze_df.write \
    .format("delta") \
    .mode(write_mode) \
    .option("mergeSchema", "true") \
    .partitionBy("partition_date") \
    .save(BRONZE_PATH)

# Summary

final_count = spark.read.format("delta").load(BRONZE_PATH).count()

print("\n" + "=" * 60)
print("  BRONZE INGEST (CSV) COMPLETE")
print("=" * 60)
print(f"  Input CSV:     {INPUT_CSV}")
print(f"  Bronze path:   {BRONZE_PATH}")
print(f"  Write mode:    {write_mode}")
print(f"  Bronze rows:   {final_count:,}")
print(f"  Schema ver:    v1.0")
print(f"  Source:        csv:backfill")
print("=" * 60)
print("\n  Bronze columns (features only, NO labels):")
for c in spark.read.format("delta").load(BRONZE_PATH).columns:
    print(f"    - {c}")
print("=" * 60)

spark.stop()