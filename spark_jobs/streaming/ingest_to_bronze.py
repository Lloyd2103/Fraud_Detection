import os
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

# Initialize Spark Session configured with Delta Lake
spark = SparkSession.builder \
    .appName("FraudDetection_BronzeIngestion") \
    .master("yarn") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Transaction JSON schema definition
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
    StructField("timestamp", TimestampType(), True),
    StructField("received_at", TimestampType(), True),
    StructField("partition_date", DateType(), True)
])

# Read stream from Kafka
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "labsoe-17:9092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "earliest") \
    .load()

# Parse JSON payload
parsed_df = kafka_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*")

# Target HDFS paths
bronze_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/bronze"
checkpoint_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/checkpoints/bronze_ingest"

# Write stream to Delta Lake Bronze table partitioned by date
query = parsed_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .partitionBy("partition_date") \
    .option("checkpointLocation", checkpoint_path) \
    .start(bronze_path)

query.awaitTermination()
