"""
Batch Lakehouse Job: Synchronize Customer Profile States to Silver Delta Lake
Decoupled from real-time streaming to prevent driver thread blocking.
Scheduled to run periodically (e.g. every 15 minutes) via Airflow.
"""

import os
import sys
import time
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    struct,
    max as spark_max,
    count as spark_count,
    sum as spark_sum,
    avg as spark_avg,
    stddev as spark_stddev,
    countDistinct,
    current_timestamp,
    lit,
)
from delta.tables import DeltaTable

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

HDFS_HOST = os.getenv("HDFS_HOST", "hdfs://labsoe-17:9000")
GOLD_RISK_SCORES = f"{HDFS_HOST}/lakehouse/fraud_detection/gold/risk_scores"
SILVER_CUSTOMER_STATES = f"{HDFS_HOST}/lakehouse/fraud_detection/silver/customer_states"


def get_spark_session():
    return (
        SparkSession.builder.appName("SyncCustomerStatesToSilver")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .master("local[2]")
        .getOrCreate()
    )


def sync_customer_states():
    t0 = time.time()
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 65)
    print("  BATCH LAKEHOUSE SYNC: CUSTOMER STATES TO SILVER DELTA")
    print("=" * 65)
    print(f"Source Table: {GOLD_RISK_SCORES}")
    print(f"Target Table: {SILVER_CUSTOMER_STATES}")
    print("-" * 65)

    if not DeltaTable.isDeltaTable(spark, GOLD_RISK_SCORES):
        print(f"Warning: Gold table does not exist at {GOLD_RISK_SCORES}. Exiting.")
        return

    gold_df = spark.read.format("delta").load(GOLD_RISK_SCORES)
    total_tx = gold_df.count()
    print(f"Read {total_tx:,} transactions from Gold Delta Lake.")

    # Aggregate latest states per account
    latest_states_df = (
        gold_df.groupBy("source_account")
        .agg(
            spark_count("transaction_id").alias("tx_count_total"),
            spark_sum("amount").alias("total_amount_total"),
            spark_avg("amount").alias("avg_amount_30d"),
            spark_stddev("amount").alias("stddev_amount_30d"),
            spark_max("timestamp").alias("last_active_time"),
            spark_max(
                struct(
                    col("timestamp").alias("ts"),
                    col("old_balance_source").alias("last_balance"),
                )
            ).alias("latest_bal_struct"),
        )
        .select(
            col("source_account").alias("account_id"),
            col("tx_count_total").cast("long").alias("tx_count_24h"),
            col("total_amount_total").cast("double").alias("total_amount_24h"),
            col("avg_amount_30d").cast("double").alias("avg_amount_30d"),
            col("stddev_amount_30d").cast("double").alias("stddev_amount_30d"),
            col("latest_bal_struct.last_balance")
            .cast("double")
            .alias("last_known_balance"),
            col("last_active_time").alias("last_active_time"),
            current_timestamp().alias("updated_at"),
        )
    )

    account_count = latest_states_df.count()
    print(f"Aggregated {account_count:,} unique customer account profiles.")

    if DeltaTable.isDeltaTable(spark, SILVER_CUSTOMER_STATES):
        print(f"Performing Delta MERGE into Silver table...")
        target_table = DeltaTable.forPath(spark, SILVER_CUSTOMER_STATES)
        target_table.alias("t").merge(
            latest_states_df.alias("s"),
            "t.account_id = s.account_id",
        ).whenMatchedUpdate(
            set={
                "tx_count_24h": col("s.tx_count_24h"),
                "total_amount_24h": col("s.total_amount_24h"),
                "avg_amount_30d": col("s.avg_amount_30d"),
                "stddev_amount_30d": col("s.stddev_amount_30d"),
                "last_known_balance": col("s.last_known_balance"),
                "last_active_time": col("s.last_active_time"),
                "updated_at": col("s.updated_at"),
            }
        ).whenNotMatchedInsertAll().execute()
    else:
        print(f"Initializing Silver table at {SILVER_CUSTOMER_STATES}...")
        latest_states_df.write.format("delta").mode("overwrite").save(
            SILVER_CUSTOMER_STATES
        )

    duration = time.time() - t0
    print(
        f"Successfully synced {account_count:,} customer profiles in {duration:.2f} seconds."
    )
    print("=" * 65)


if __name__ == "__main__":
    sync_customer_states()
