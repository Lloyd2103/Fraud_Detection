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

# KHỞI TẠO SPARK
spark = SparkSession.builder \
    .appName("FraudDetection_BronzeIngestion") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Tắt các log thừa để tránh nghẽn I/O đĩa cứng Master khi chạy streaming dài hạn
spark.sparkContext.setLogLevel("WARN")

# Định nghĩa cấu trúc Schema JSON
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

# Đọc luồng dữ liệu thời gian thực từ Kafka Broker
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "labsoe-17:9092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "earliest") \
    .load()

# Giải mã gói tin JSON từ Kafka payload
parsed_df = kafka_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*")

# Xác định đường dẫn lưu trữ tập trung trên HDFS phân tán
bronze_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/bronze"
checkpoint_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/checkpoints/bronze_ingest"

# Ghi luồng dữ liệu liên tục vào tầng Bronze Delta Table phân vùng theo ngày
# Thêm khoảng thời gian xử lý micro-batch (trigger) để kiểm soát RAM ổn định cho máy
query = parsed_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .partitionBy("partition_date") \
    .option("checkpointLocation", checkpoint_path) \
    .trigger(processingTime="5 seconds") \
    .start(bronze_path)

query.awaitTermination()
