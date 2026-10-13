"""
MERGE 2 (DeTai2.pdf Section 2.7):
Synchronizes manual inspection verdicts from CockroachDB serving store into Gold Delta Lake (gold.risk_scores).
Updates 'inspection_status' when inspectors complete their investigation.
"""
import os
import sys
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
from delta.tables import DeltaTable


def clean_path(p):
    if p and p.startswith("hdfs:///"):
        return "/" + p[len("hdfs:///"):].lstrip("/")
    return p


GOLD_RISK_SCORES = clean_path(os.getenv("GOLD_RISK_SCORES", "/lakehouse/fraud_detection/gold/risk_scores"))

COCKROACH_HOST     = os.getenv("COCKROACH_HOST", "192.168.80.201")
COCKROACH_PORT     = os.getenv("COCKROACH_PORT", "26257")
COCKROACH_DB       = os.getenv("COCKROACH_DB", "system_db")
COCKROACH_USER     = os.getenv("COCKROACH_USER", "admin")
COCKROACH_PASSWORD = os.getenv("COCKROACH_PASSWORD", "admin123")
COCKROACH_JDBC_URL = os.getenv("COCKROACH_JDBC_URL", f"jdbc:postgresql://{COCKROACH_HOST}:{COCKROACH_PORT}/{COCKROACH_DB}?sslmode=disable")


def main():
    print("=" * 80)
    print("--- DELTA LAKE MERGE 2: SYNC INSPECTION VERDICTS TO GOLD LAYER ---")
    print(f"Target Gold Table: {GOLD_RISK_SCORES}")
    print("=" * 80)

    spark = SparkSession.builder \
        .appName("FraudDetection_Sync_Verdicts_To_Gold") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    if not DeltaTable.isDeltaTable(spark, GOLD_RISK_SCORES):
        print(f"[ERROR] Delta table not found at: {GOLD_RISK_SCORES}")
        spark.stop()
        sys.exit(1)

    print("\n[STEP 1] Reading decided inspection verdicts from CockroachDB...")
    try:
        verdicts_df = spark.read \
            .format("jdbc") \
            .option("url", COCKROACH_JDBC_URL) \
            .option("dbtable", "(SELECT transaction_id, inspection_status, updated_at FROM transactions WHERE inspection_status IN ('CONFIRMED_FRAUD', 'CLEARED_LEGITIMATE', 'PROCESSED')) AS v") \
            .option("user", COCKROACH_USER) \
            .option("password", COCKROACH_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .load()

        verdict_count = verdicts_df.count()
        print(f"Found {verdict_count:,} decided verdicts in CockroachDB serving store.")
        if verdict_count > 0:
            verdicts_df.show(5, truncate=False)
    except Exception as e_read:
        print(f"[ERROR] Failed to query CockroachDB: {e_read}")
        spark.stop()
        sys.exit(1)

    if verdict_count == 0:
        print("No completed verdicts to merge. Exiting.")
        spark.stop()
        return

    print("\n[STEP 2] Executing Delta MERGE into gold.risk_scores (Section 2.7)...")
    gold_table = DeltaTable.forPath(spark, GOLD_RISK_SCORES)

    gold_table.alias("gold").merge(
        source=verdicts_df.alias("v"),
        condition="gold.transaction_id = v.transaction_id"
    ).whenMatchedUpdate(set={
        "inspection_status": col("v.inspection_status")
    }).execute()

    print(f"✓ Successfully merged {verdict_count} inspection verdicts into Gold Delta Lake!")
    spark.stop()


if __name__ == "__main__":
    main()
