import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, max as spark_max
from delta.tables import DeltaTable

# 🛠️ KHỞI TẠO SPARK
spark = SparkSession.builder \
    .appName("FraudDetection_BronzeToSilver") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

# Tắt bớt log rác để màn hình Terminal/Airflow sạch sẽ hơn
spark.sparkContext.setLogLevel("WARN")

# Định nghĩa các đường dẫn lưu trữ trên hệ thống phân tán HDFS
# Sử dụng cấu trúc thư mục chuẩn theo yêu cầu đồ án
bronze_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/bronze"
silver_transactions_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/silver/transactions"
silver_states_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/silver/customer_states"
quarantine_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/_quarantine"

# 1. Đọc dữ liệu từ bảng Bronze Delta Table trên HDFS
print("Reading Bronze Delta table...")
bronze_df = spark.read.format("delta").load(bronze_path)

# 2. Lọc và cô lập các bản ghi không hợp lệ (Invalid Records)
invalid_df = bronze_df.filter(
    (col("amount") <= 0) | 
    col("transaction_id").isNull() | 
    col("source_account").isNull() |
    col("dest_account").isNull()
)

# Tránh dùng .rdd.isEmpty() vì nó kích hoạt một job thu thập dữ liệu về Master gây tốn RAM.
# Sử dụng invalid_df.take(1) tối ưu hiệu năng và tài nguyên hơn rất nhiều.
if len(invalid_df.take(1)) > 0:
    print("Writing invalid records to quarantine directory...")
    invalid_df.write.format("delta").mode("append").save(quarantine_path)

# 3. Lọc lấy các bản ghi hợp lệ và loại bỏ trùng lặp mã giao dịch
valid_df = bronze_df.filter(
    (col("amount") > 0) & 
    col("transaction_id").isNotNull() & 
    col("source_account").isNotNull() &
    col("dest_account").isNotNull()
).dropDuplicates(["transaction_id"])

# 4. Lưu trữ dữ liệu sạch vào tầng Silver Transactions (Có phân vùng theo ngày)
print("Saving cleaned transactions to Silver layer...")
valid_df.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("partition_date") \
    .option("overwriteSchema", "true") \
    .save(silver_transactions_path)

# 5. Tính toán trạng thái tổng hợp của khách hàng (Customer States)
print("Computing Customer States...")
customer_states = valid_df.groupBy("source_account").agg(
    count("transaction_id").alias("trans_count_total"),
    spark_max("timestamp").alias("last_active_time"),
    spark_max("new_balance_source").alias("last_known_balance")
).withColumnRenamed("source_account", "account_id")

# 6. Thực hiện MERGE / Upsert dữ liệu thông minh vào tầng Silver Customer States
if DeltaTable.isDeltaTable(spark, silver_states_path):
    print("Executing Delta MERGE into Silver Customer States...")
    delta_silver = DeltaTable.forPath(spark, silver_states_path)
    delta_silver.alias("target").merge(
        customer_states.alias("source"),
        "target.account_id = source.account_id"
    ).whenMatchedUpdateAll() \
     .whenNotMatchedInsertAll() \
     .execute()
else:
    print("Creating Silver Customer States table for the first time...")
    customer_states.write.format("delta").mode("overwrite").save(silver_states_path)

print("Bronze to Silver ETL pipeline executed successfully.")

# Dừng Spark session để giải phóng tài nguyên lập tức cho cụm
spark.stop()
