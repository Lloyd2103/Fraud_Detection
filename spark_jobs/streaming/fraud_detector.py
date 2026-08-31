import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_json, struct, abs as spark_abs, current_timestamp
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType
)
from pyspark.ml import PipelineModel

# Khoi tao SparkSession cho Cluster Mode
spark = SparkSession.builder \
    .appName("FraudDetection_Realtime_Detector") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

model_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/models/random_forest_fraud_model"
checkpoint_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/checkpoints/realtime_fraud_detector"

# 1. Load trained ML Pipeline Model tu HDFS
model = PipelineModel.load(model_path)

# 2. Schema Kafka payload
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

# 3. Read Stream tu Kafka Topic transactions
kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.80.200:9092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# 4. Feature Engineering
parsed_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("trans_count_total", col("amount") * 0 + 1) \
    .withColumn("error_balance_source", spark_abs((col("old_balance_source") - col("amount")) - col("new_balance_source"))) \
    .withColumn("error_balance_dest", spark_abs((col("old_balance_dest") + col("amount")) - col("new_balance_dest")))

features_df = parsed_df.na.fill({
    "trans_count_total": 1,
    "error_balance_source": 0.0,
    "error_balance_dest": 0.0,
    "old_balance_source": 0.0,
    "new_balance_source": 0.0,
    "old_balance_dest": 0.0,
    "new_balance_dest": 0.0
})

# 5. ML Inference
scored_df = model.transform(features_df)

# 6. Loc cac giao dich gian lan
fraud_alerts = scored_df.filter(col("prediction") == 1.0).select(
    col("transaction_id").alias("key"),
    to_json(struct(
        col("transaction_id"),
        col("source_account"),
        col("dest_account"),
        col("trans_type"),
        col("amount"),
        col("channel"),
        col("prediction").alias("fraud_prediction"),
        current_timestamp().alias("alert_generated_at")
    )).alias("value")
)

# 7. Write ket qua ra Kafka topic fraud_alerts
query = fraud_alerts.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.80.200:9092") \
    .option("topic", "fraud_alerts") \
    .option("checkpointLocation", checkpoint_path) \
    .outputMode("append") \
    .start()

spark.streams.awaitAnyTermination()