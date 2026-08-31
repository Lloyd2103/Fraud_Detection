import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count, lit
from pyspark.sql.window import Window
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier, RandomForestClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator

# KHỞI TẠO SPARK ML ENGINE
spark = SparkSession.builder \
    .appName("FraudDetection_Advanced_ML_Training") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Đọc nguồn dữ liệu đặc trưng Point-in-Time sạch đã lưu ở bước trước (Tránh rò rỉ dữ liệu)
features_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/features"
model_save_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/models/gbt_fraud_model"

print("Loading Point-in-Time Feature Dataset...")
clean_df = spark.read.format("delta").load(features_path)

# ==================================================================
# ĐIỀU KIỆN BẮT BUỘC 1: CHIA DỮ LIỆU THEO THỜI GIAN CHUẨN (TIME-BASED SPLIT)
# Tuyệt đối không dùng randomSplit để tránh rò rỉ tương lai
# ==================================================================
print("Executing Time-based data splitting (70% Train, 15% Val, 15% Test)...")
total_count = clean_df.count()

# Sắp xếp toàn bộ tập dữ liệu theo thứ tự thời gian tăng dần để đánh số thứ tự dòng
window_time = Window.orderBy("timestamp")
ordered_df = clean_df.withColumn("row_idx", row_number().over(window_time))

train_cutoff = int(total_count * 0.70)
val_cutoff = int(total_count * 0.85)

train_raw = ordered_df.filter(col("row_idx") <= train_cutoff).drop("row_idx")
val_df = ordered_df.filter((col("row_idx") > train_cutoff) & (col("row_idx") <= val_cutoff)).drop("row_idx")
test_df = ordered_df.filter(col("row_idx") > val_cutoff).drop("row_idx")

# ==================================================================
# ĐIỀU KIỆN BẮT BUỘC 2: XỬ LÝ MẤT CÂN BẰNG NHÃN (UNDERSAMPLING LỚP ÂM TỶ LỆ 1:20)
# ==================================================================
print("Applying Negative Class Undersampling (Ratio 1:20)...")
fraud_mẫu = train_raw.filter(col("is_fraud_label") == 1)
safe_mẫu = train_raw.filter(col("is_fraud_label") == 0)

# Tính toán tỷ lệ lấy mẫu để ép lớp âm về đúng tỷ lệ 1:20 so với lớp dương
sample_fraction = (fraud_mẫu.count() * 20) / safe_mẫu.count()
if sample_fraction > 1.0: sample_fraction = 1.0

safe_undersampled = safe_mẫu.sample(False, sample_fraction, seed=42)
train_df = fraud_mẫu.union(safe_undersampled)

# XỬ LÝ MẤT CÂN BẰNG CÁCH 2: Tính toán trọng số lớp nghịch đảo (weightCol)
total_train = train_df.count()
fraud_train = train_df.filter(col("is_fraud_label") == 1).count()
safe_train = total_train - fraud_train

fraud_weight = total_train / (2.0 * fraud_train)
safe_weight = total_train / (2.0 * safe_train)

train_df = train_df.withColumn("class_weight", when(col("is_fraud_label") == 1, fraud_weight).otherwise(safe_weight))

# ==================================================================
# XÂY DỰNG PIPELINE TIỀN XỬ LÝ ĐẶC TRƯNG
# ==================================================================
type_indexer = StringIndexer(inputCol="trans_type", outputCol="trans_type_idx", handleInvalid="keep")
channel_indexer = StringIndexer(inputCol="channel", outputCol="channel_idx", handleInvalid="keep")

encoder = OneHotEncoder(
    inputCols=["trans_type_idx", "channel_idx"],
    outputCols=["trans_type_vec", "channel_vec"]
)

feature_cols = [
    "amount", "old_balance_source", "new_balance_source", "old_balance_dest", "new_balance_dest",
    "trans_count_total", "error_balance_source", "error_balance_dest", "trans_type_vec", "channel_vec"
]

assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
scaler = StandardScaler(inputCol="raw_features", outputCol="features", withStd=True, withMean=False)

# ==================================================================
# ĐIỀU KIỆN BẮT BUỘC 3: THUẬT TOÁN CHÍNH GBTCLASSIFIER (GRADIENT BOOSTED TREES)
# ==================================================================
print("Initializing Main Model: GBTClassifier...")
gbt_classifier = GBTClassifier(
    featuresCol="features",
    labelCol="is_fraud_label",
    weightCol="class_weight", # Gắn trọng số lớp nghịch đảo để tối ưu
    maxIter=50,
    maxDepth=5,
    seed=42
)

pipeline = Pipeline(stages=[type_indexer, channel_indexer, encoder, assembler, scaler, gbt_classifier])

print("Starting Distributed GBT Model Training on Workers...")
model = pipeline.fit(train_df)

# ==================================================================
# ĐÁNH GIÁ MÔ HÌNH TRÊN TẬP TEST Kèm METRIC ĐẶC TẢ (PR-AUC, ROC-AUC)
# ==================================================================
print("Evaluating GBT Model on Test Data...")
predictions = model.transform(test_df)

evaluator_roc = BinaryClassificationEvaluator(labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
evaluator_pr = BinaryClassificationEvaluator(labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderPR")

auc_roc = evaluator_roc.evaluate(predictions)
auc_pr = evaluator_pr.evaluate(predictions)

print("=" * 60)
print(f"Main Model GBT Area Under ROC (AUC-ROC): {auc_roc:.4f}")
print(f"Main Model GBT Area Under PR  (AUC-PR) : {auc_pr:.4f}")
print("=" * 60)

# TRÍCH XUẤT FEATURE IMPORTANCES THEO YÊU CẦU ĐẶC TẢ
gbt_model = model.stages[-1]
importances = gbt_model.featureImportances.toArray()
print("\n--- FEATURE IMPORTANCES TRÍCH XUẤT TỪ GBT ---")
for col_name, imp in zip(feature_cols, importances):
    print(f"Feature: {col_name:<25} | Importance: {imp:.4f}")

print(f"\nSaving trained GBT PipelineModel to HDFS: {model_save_path}...")
model.write().overwrite().save(model_save_path)
print("Model training and export finished successfully.")

spark.stop()
