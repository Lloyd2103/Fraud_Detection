import os
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, sum as spark_sum, round as spark_round, avg, current_timestamp,
    coalesce, lit
)
from delta.tables import DeltaTable

spark = SparkSession.builder \
    .appName("FraudDetection_SilverToGold_Analytics") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

SILVER_TRANSACTIONS = os.getenv("SILVER_TRANSACTIONS")
GOLD_SUMMARY        = os.getenv("GOLD_SUMMARY")

COCKROACH_HOST     = os.getenv("COCKROACH_HOST")
COCKROACH_PORT     = os.getenv("COCKROACH_PORT")
COCKROACH_DB       = os.getenv("COCKROACH_DB")
COCKROACH_USER     = os.getenv("COCKROACH_USER")
COCKROACH_PASSWORD = os.getenv("COCKROACH_PASSWORD")
COCKROACH_JDBC_URL = os.getenv("COCKROACH_JDBC_URL")

# 1. Read Clean Silver Transactions from HDFS
if not DeltaTable.isDeltaTable(spark, SILVER_TRANSACTIONS):
    raise ValueError(f"Silver transactions table not found at {SILVER_TRANSACTIONS}. Run bronze_to_silver.py first.")

print("--- READING SILVER TRANSACTIONS FROM HDFS ---")
transactions_df = spark.read.format("delta").load(SILVER_TRANSACTIONS)

# Defensive checks for columns
safe_df = transactions_df \
    .withColumn("channel", coalesce(col("channel"), lit("UNKNOWN"))) \
    .withColumn("trans_type", coalesce(col("trans_type"), lit("UNKNOWN")))

if "is_fraud_label" in safe_df.columns:
    fraud_exprs = [
        coalesce(spark_sum("is_fraud_label"), lit(0)).cast("long").alias("total_fraud_cases"),
        coalesce(spark_round(avg("is_fraud_label") * 100, 4), lit(0.0)).alias("fraud_rate_percentage")
    ]
else:
    fraud_exprs = [
        lit(0).cast("long").alias("total_fraud_cases"),
        lit(0.0).alias("fraud_rate_percentage")
    ]

# 2. Executive Analytics Aggregation
summary_df = safe_df.groupBy("trans_type", "channel").agg(
    count("transaction_id").alias("total_transactions"),
    coalesce(spark_round(spark_sum("amount"), 2), lit(0.0)).alias("total_volume"),
    *fraud_exprs
).withColumn("calculated_at", current_timestamp())

print("=== EXECUTIVE FRAUD SUMMARY BY CHANNEL & TYPE ===")
summary_df.show(truncate=False)

# 3. Store in HDFS Delta Lake
print(f"--- UPSERTING INTO HDFS DELTA LAKE: {GOLD_SUMMARY} ---")
if DeltaTable.isDeltaTable(spark, GOLD_SUMMARY):
    gold_table = DeltaTable.forPath(spark, GOLD_SUMMARY)
    gold_table.alias("target").merge(
        source=summary_df.alias("source"),
        condition="target.trans_type = source.trans_type AND target.channel = source.channel"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    summary_df.write.format("delta").mode("overwrite").save(GOLD_SUMMARY)
    # Enable Change Data Feed
    try:
        spark.sql(f"ALTER TABLE delta.`{GOLD_SUMMARY}` SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    except Exception as e_cdf:
        print(f"Note: Could not set CDF on gold summary: {e_cdf}")

    # Add Quality Constraints
    try:
        spark.sql(f"ALTER TABLE delta.`{GOLD_SUMMARY}` ADD CONSTRAINT check_fraud_cases_logic CHECK (total_fraud_cases <= total_transactions)")
        spark.sql(f"ALTER TABLE delta.`{GOLD_SUMMARY}` ADD CONSTRAINT check_volume_non_negative CHECK (total_volume >= 0)")
    except Exception as e_c:
        print(f"Note: Delta constraint check: {e_c}")

# 4. Sync to CockroachDB Serving Store
print("--- SYNCING TO COCKROACHDB SERVING STORE ---")
try:
    summary_df.write \
        .format("jdbc") \
        .option("url", COCKROACH_JDBC_URL) \
        .option("dbtable", "fraud_summary") \
        .option("user", COCKROACH_USER) \
        .option("password", COCKROACH_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .option("truncate", "true") \
        .mode("overwrite") \
        .save()
    print("--- Sync to CockroachDB succeeded! ---")
except Exception as e_sync:
    print(f"[ERROR] Sync to CockroachDB failed: {e_sync}")
    raise e_sync

print("--- SILVER TO GOLD ANALYTICS COMPLETED SUCCESSFULLY ---")
spark.stop()
