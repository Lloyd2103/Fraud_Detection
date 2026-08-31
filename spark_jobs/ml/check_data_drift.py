import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, stddev, abs as spark_abs

print("--- INITIALIZING DATA DRIFT DETECTION ENGINE ---")

# 1. Khởi tạo Spark Session Standalone
spark = SparkSession.builder \
    .appName("FraudDetection_DataDrift_Monitoring") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Định nghĩa đường dẫn 2 tập dữ liệu cần đối chiếu trên HDFS
baseline_features_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/features"
new_transactions_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/silver/transactions"

try:
    print("Reading Baseline Features (Historical Data used for training)...")
    baseline_df = spark.read.format("delta").load(baseline_features_path)
    
    print("Reading Target Data (New incoming Silver transactions this week)...")
    target_df = spark.read.format("delta").load(new_transactions_path)
    
    # 2. Tính toán các chỉ số phân phối thống kê mô tả (Mean, StdDev) cho trường 'amount'
    print("Computing distribution metrics for transaction amount...")
    baseline_stats = baseline_df.select(avg("amount").alias("mean"), stddev("amount").alias("stddev")).collect()[0]
    target_stats = target_df.select(avg("amount").alias("mean"), stddev("amount").alias("stddev")).collect()[0]
    
    mean_baseline = baseline_stats["mean"] or 0.0
    std_baseline = baseline_stats["stddev"] or 1.0
    
    mean_target = target_stats["mean"] or 0.0
    
    # 3. Áp dụng thuật toán kiểm định độ dịch chuyển (Population Stability Index đơn giản hóa qua Z-Score)
    drift_score = abs(mean_target - mean_baseline) / (std_baseline / (target_df.count() ** 0.5))
    
    # Ngưỡng chấp nhận dao động phân phối (Thường đặt là 2.0 hoặc 3.0 trong hệ thống giám sát)
    DRIFT_THRESHOLD = 3.0
    
    print("=" * 60)
    print(f"Baseline Mean Amount : {mean_baseline:.4f}")
    print(f"Target Mean Amount   : {mean_target:.4f}")
    print(f"Calculated Drift Score: {drift_score:.4f}")
    print("=" * 60)
    
    if drift_score > DRIFT_THRESHOLD:
        print("ALERT: Data Drift detected! The distribution of transaction amounts has changed significantly.")
        print("Status: TRIGGER_RETRAIN")
        # Thoát với mã code đặc biệt để Airflow biết đường rẽ nhánh kích hoạt job re-train
        sys.exit(10)
    else:
        print("SUCCESS: No significant Data Drift detected. Model behavior remains stable.")
        print("Status: KEEP_CURRENT_MODEL")
        sys.exit(0)

except Exception as e:
    print(f"Error during drift detection pipeline: {str(e)}")
    sys.exit(1)
    
finally:
    spark.stop()
