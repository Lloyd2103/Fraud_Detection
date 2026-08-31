import sys
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import col, count, max as spark_max, abs, coalesce, lit

# KHỞI TẠO SPARK ML FEATURE STORE
spark = SparkSession.builder \
    .appName("FraudDetection_PointInTime_FeatureStore") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

silver_transactions_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/silver/transactions"
features_save_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/features"

print("Reading Clean Silver Transactions...")
tx_df = spark.read.format("delta").load(silver_transactions_path)

print("Cài đặt cấu hình Window Function bọc thép Point-in-Time Join...")
# RÀNG BUỘC CHỐNG DATA LEAKAGE: Chỉ gom nhóm dữ liệu kể từ dòng đầu tiên 
# cho đến sát trước dòng hiện tại (rowsBetween UnboundedPreceding to -1)
pit_window = Window.partitionBy("source_account") \
                   .orderBy("timestamp") \
                   .rowsBetween(Window.unboundedPreceding, -1)

print("Đang tiến hành tái xây dựng tập đặc trưng lịch sử không rò rỉ tương lai...")
feature_store_df = tx_df.withColumn(
    # Tính tổng số giao dịch TRƯỚC khi giao dịch hiện tại diễn ra
    "trans_count_total", 
    count("transaction_id").over(pit_window)
).select(
    col("transaction_id"),
    col("source_account"),
    col("dest_account"),
    col("trans_type"),
    col("amount"),
    col("old_balance_source"),
    col("new_balance_source"),
    col("old_balance_dest"),
    col("new_balance_dest"),
    col("channel"),
    col("is_fraud_label"),
    col("timestamp"),
    col("partition_date"),
    coalesce(col("trans_count_total"), lit(0)).alias("trans_count_total"),
    abs((col("old_balance_source") - col("amount")) - col("new_balance_source")).alias("error_balance_source"),
    abs((col("old_balance_dest") + col("amount")) - col("new_balance_dest")).alias("error_balance_dest")
)

print(f"Saving Clean Point-in-Time Feature Store to HDFS: {features_save_path}")
feature_store_df.write \
    .format("delta") \
    .mode("overwrite") \
    .save(features_save_path)

print("Point-in-Time Feature Dataset built successfully.")
spark.stop()
