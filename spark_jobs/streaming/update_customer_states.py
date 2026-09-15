# Standalone customer state aggregation job into Silver layer
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, current_timestamp, count, max as spark_max, 
    sum as spark_sum, avg, stddev, countDistinct, array, lit, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType
)
from delta.tables import DeltaTable

spark = SparkSession.builder \
    .appName("FraudDetection_UpdateCustomerStates") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.200:9092")
INPUT_TOPIC = "transactions"
SILVER_STATES = "hdfs:///lakehouse/fraud_detection/silver/customer_states"
CHECKPOINT_PATH = "hdfs:///lakehouse/fraud_detection/checkpoints/update_customer_states"

schema = StructType([
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
    StructField("is_fraud_label", IntegerType(), True),
    StructField("timestamp", StringType(), True)
])

print(f"[INFO] Subscribing to Kafka topic '{INPUT_TOPIC}' for state maintenance...")
kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", INPUT_TOPIC) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

parsed_stream_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", to_timestamp(col("timestamp"))) \
    .withWatermark("event_time", "1 minute")

def update_states_microbatch(microBatchDF, batchId):
    if microBatchDF.rdd.isEmpty():
        return

    batch_count = microBatchDF.count()
    print(f"--- [Stateful Batch {batchId}] Aggregating {batch_count} records ---")

    try:
        batch_states = microBatchDF.groupBy("source_account").agg(
            count("transaction_id").alias("b_count"),
            spark_sum("amount").alias("b_amount"),
            spark_max("event_time").alias("b_last_time"),
            spark_max("new_balance_source").alias("b_last_balance"),
            countDistinct("dest_account").alias("b_dest_count")
        ).withColumnRenamed("source_account", "account_id")

        if DeltaTable.isDeltaTable(spark, SILVER_STATES):
            deltaTable = DeltaTable.forPath(spark, SILVER_STATES)
            deltaTable.alias("target").merge(
                batch_states.alias("source"),
                "target.account_id = source.account_id"
            ).whenMatchedUpdate(set={
                "tx_count_1h": col("target.tx_count_1h") + col("source.b_count"),
                "tx_count_24h": col("target.tx_count_24h") + col("source.b_count"),
                "tx_count_7d": col("target.tx_count_7d") + col("source.b_count"),
                "trans_count_total": col("target.trans_count_total") + col("source.b_count"),
                "total_amount_24h": col("target.total_amount_24h") + col("source.b_amount"),
                "avg_amount_30d": (col("target.total_amount_24h") + col("source.b_amount")) / (col("target.trans_count_total") + col("source.b_count")),
                "unique_dest_accounts_24h": col("target.unique_dest_accounts_24h") + col("source.b_dest_count"),
                "last_active_time": col("source.b_last_time"),
                "last_known_balance": col("source.b_last_balance"),
                "updated_at": current_timestamp()
            }).whenNotMatchedInsert(values={
                "account_id": col("source.account_id"),
                "tx_count_1h": col("source.b_count"),
                "tx_count_24h": col("source.b_count"),
                "tx_count_7d": col("source.b_count"),
                "trans_count_total": col("source.b_count"),
                "total_amount_24h": col("source.b_amount"),
                "avg_amount_30d": col("source.b_amount") / col("source.b_count"),
                "stddev_amount_30d": lit(0.0),
                "unique_dest_accounts_24h": col("source.b_dest_count"),
                "frequent_tx_hours": array(lit(8), lit(12), lit(20)),
                "last_active_time": col("source.b_last_time"),
                "last_known_balance": col("source.b_last_balance"),
                "updated_at": current_timestamp()
            }).execute()
            print(f"[Stateful Batch {batchId}] Delta MERGE successfully accumulated into Silver.")
        else:
            init_df = batch_states.select(
                col("account_id"),
                col("b_count").alias("tx_count_1h"),
                col("b_count").alias("tx_count_24h"),
                col("b_count").alias("tx_count_7d"),
                col("b_count").alias("trans_count_total"),
                col("b_amount").alias("total_amount_24h"),
                (col("b_amount") / col("b_count")).alias("avg_amount_30d"),
                lit(0.0).alias("stddev_amount_30d"),
                col("b_dest_count").alias("unique_dest_accounts_24h"),
                array(lit(8), lit(12), lit(20)).alias("frequent_tx_hours"),
                col("b_last_time").alias("last_active_time"),
                col("b_last_balance").alias("last_known_balance"),
                current_timestamp().alias("updated_at")
            )
            init_df.write.format("delta").mode("overwrite").save(SILVER_STATES)
            print(f"[Stateful Batch {batchId}] Initialized Delta Table Silver States.")
    except Exception as e_state:
        print(f"[Stateful Batch {batchId}] State Update Error: {e_state}")

state_query = parsed_stream_df.writeStream \
    .queryName("Customer_States_Aggregator") \
    .trigger(processingTime="10 seconds") \
    .option("checkpointLocation", CHECKPOINT_PATH) \
    .foreachBatch(update_states_microbatch) \
    .start()

state_query.awaitTermination()