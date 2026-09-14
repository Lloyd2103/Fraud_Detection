import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType,
    TimestampType,
    DateType
)

print("--- INITIALIZING SPARK STRUCTURED STREAMING (STANDALONE MODE) ---")

spark = SparkSession.builder \
    .appName("FraudDetection_BronzeIngestion") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
    .config("spark.sql.adaptive.enabled", "false") \
    .config("spark.network.timeout", "600s") \
    .config("spark.executor.heartbeatInterval", "60s") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

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
    StructField("timestamp", StringType(), True),
    StructField("received_at", StringType(), True),
    StructField("partition_date", StringType(), True)
])

# Centralized Environment Configuration
MASTER_IP = os.getenv("MASTER_IP", "192.168.80.200")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{MASTER_IP}:9092")
HDFS_HOST = os.getenv("HDFS_HOST", "labsoe-17")

print(f"--- CONNECTING TO KAFKA BROKER ({KAFKA_BOOTSTRAP_SERVERS}) ---")

kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("kafka.request.timeout.ms", "180000") \
    .option("kafka.session.timeout.ms", "120000") \
    .option("kafka.fetch.max.wait.ms", "30000") \
    .option("maxOffsetsPerTrigger", "3000") \
    .load()


from pyspark.sql.functions import from_json, col, coalesce, current_timestamp, to_timestamp

# Configure stream parsing and partition date
parsed_stream_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("timestamp", coalesce(to_timestamp(col("timestamp")), current_timestamp())) \
    .withColumn("partition_date", col("timestamp").cast(DateType()))




bronze_table_path = f"hdfs://{HDFS_HOST}:9000/lakehouse/fraud_detection/bronze"
checkpoint_hdfs_path = f"hdfs://{HDFS_HOST}:9000/lakehouse/fraud_detection/checkpoints/bronze_ingest"



print(f"--- STREAMING DATA WRITING TO BRONZE DELTA LAKE: {bronze_table_path} ---")

query = parsed_stream_df.writeStream \
    .queryName("Bronze_Kafka_Ingestion") \
    .format("delta") \
    .outputMode("append") \
    .partitionBy("partition_date") \
    .option("checkpointLocation", checkpoint_hdfs_path) \
    .option("mergeSchema", "true") \
    .trigger(processingTime="5 seconds") \
    .start(bronze_table_path)


query.awaitTermination()

