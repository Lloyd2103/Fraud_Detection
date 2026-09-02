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

# 1. Khởi tạo Spark Session tích hợp Delta Lake
spark = SparkSession.builder \
    .appName("FraudDetection_BronzeIngestion") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
    .config("spark.sql.adaptive.enabled", "false") \
    .config("spark.network.timeout", "600s") \
    .config("spark.executor.heartbeatInterval", "60s") \
    .getOrCreate()


# Giảm thiểu tối đa log rác ghi xuống ổ đĩa Master
spark.sparkContext.setLogLevel("WARN")

# 2. Định nghĩa Schema khớp chính xác với luồng dữ liệu giao dịch
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

print("--- CONNECTING TO KAFKA BROKER (192.168.80.200:9092) ---")

# 3. Kết nối luồng đọc thời gian thực từ Kafka Broker
kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.80.200:9092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .option("kafka.request.timeout.ms", "120000") \          
    .option("kafka.session.timeout.ms", "60000") \         
    .option("kafka.fetch.max.wait.ms", "10000") \           
    .option("maxOffsetsPerTrigger", "50000") \              
    .load()

# 4. Parse JSON Payload và CẤU HÌNH WATERMARK BẮT BUỘC
# Thiết lập ngưỡng chịu lỗi cho dữ liệu đến muộn/lệch thứ tự tối đa 30 giây dựa trên cột Event Time (timestamp)
parsed_stream_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*") \
    .withWatermark("timestamp", "30 seconds") 

# 5. Định nghĩa các đường dẫn lưu trữ tập trung bắt buộc trên HDFS
bronze_table_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/bronze"
checkpoint_hdfs_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/checkpoints/bronze_ingest"

print(f"--- STREAMING DATA WRITING TO BRONZE DELTA LAKE: {bronze_table_path} ---")

# 6. Thực hiện ghi luồng phân tán xuống HDFS (Có cơ chế Trigger & Checkpoint bảo vệ)
query = parsed_stream_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .partitionBy("partition_date") \
    .option("checkpointLocation", checkpoint_hdfs_path) \
    .trigger(processingTime="5 seconds") \
    .start(bronze_table_path)

# Giữ tiến trình chạy liên tục không ngắt quãng
query.awaitTermination()
