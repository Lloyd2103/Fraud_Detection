import os
import sys
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, desc, current_timestamp
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number
from pyspark.ml import PipelineModel
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.functions import vector_to_array
from delta.tables import DeltaTable

print("=" * 85)
print("--- BANK AUDIT: TIME TRAVEL MODEL & DATA REPRODUCIBILITY (Textbook 6.4.4 / DeTai2.pdf 2.7) ---")
print("=" * 85)

spark = SparkSession.builder \
    .appName("FraudDetection_Delta_TimeTravel_Audit") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

FEATURES_PATH   = os.getenv("FEATURES_PATH") 
MODEL_PATH      = os.getenv("MODEL_PATH")
CANDIDATE_PATH  = os.getenv("CANDIDATE_PATH")
COMPARISON_PATH = os.getenv("COMPARISON_PATH")


# 1. Audit Trail: Inspect Delta Commit History (Textbook Mã 6.7)
print("\n[STEP 1] Inspecting Delta Lake Transaction History for Features Dataset...")
target_version = 0
try:
    history_df = spark.sql(f"DESCRIBE HISTORY delta.`{FEATURES_PATH}`")
    print("\nCommit History (Recent 5 versions):")
    history_df.select("version", "timestamp", "operation", "userName").show(5, truncate=False)
    
    # Check if target version passed via env or default to latest/first available
    versions_list = [row["version"] for row in history_df.select("version").collect()]
    if versions_list:
        target_version = int(os.getenv("AUDIT_VERSION", versions_list[0]))
    print(f">> Selected Audit Target Version: {target_version}")
except Exception as e_hist:
    print(f"Notice inspecting history on {FEATURES_PATH}: {e_hist}")
    target_version = 0

# 2. Re-create Training/Evaluation Dataset via VERSION AS OF
print(f"\n[STEP 2] Reproducing Training Dataset via 'SELECT ... VERSION AS OF {target_version}'...")
try:
    time_travel_df = spark.read.format("delta").option("versionAsOf", target_version).load(FEATURES_PATH)
    record_count = time_travel_df.count()
    fraud_count = time_travel_df.filter(col("is_fraud_label") == 1).count()
    print(f">> Version {target_version} successfully loaded: {record_count:,} records (Fraud: {fraud_count:,})")
except Exception as e_load:
    print(f"Error loading version {target_version}: {e_load}")
    spark.stop()
    sys.exit(0)

# 3. Load Model and Recompute Evaluation Metrics
print("\n[STEP 3] Executing Model Inference on Historical Snapshot for Bank Audit...")
model = None
for path in [MODEL_PATH, CANDIDATE_PATH]:
    try:
        model = PipelineModel.load(path)
        print(f">> Loaded model for evaluation from: {path}")
        break
    except Exception:
        continue

if model is None:
    print("No trained PipelineModel found for audit verification.")
    spark.stop()
    sys.exit(0)

predictions = model.transform(time_travel_df)

# Evaluate Area Under PR and ROC
evaluator_pr = BinaryClassificationEvaluator(
    labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderPR"
)
evaluator_roc = BinaryClassificationEvaluator(
    labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderROC"
)
reproduced_pr_auc = evaluator_pr.evaluate(predictions)
reproduced_roc_auc = evaluator_roc.evaluate(predictions)

# Compute Precision@200
daily_top200 = predictions \
    .withColumn("prob_fraud", vector_to_array(col("probability"))[1]) \
    .withColumn("rn", row_number().over(Window.partitionBy("partition_date").orderBy(desc("prob_fraud")))) \
    .filter(col("rn") <= 200)

total_top200 = daily_top200.count()
tp_count = daily_top200.filter(col("is_fraud_label") == 1).count()
reproduced_p200 = (tp_count / float(total_top200)) if total_top200 > 0 else 0.0

# 4. Compare with Logged Gold Metrics
logged_metrics = None
try:
    if DeltaTable.isDeltaTable(spark, COMPARISON_PATH):
        comp_df = spark.read.format("delta").load(COMPARISON_PATH)
        gbt_row = comp_df.filter(col("algorithm") == "GBTClassifier").first()
        if gbt_row:
            logged_metrics = {
                "precision_at_200": float(gbt_row["precision_at_200"]),
                "pr_auc": float(gbt_row["pr_auc"]),
                "roc_auc": float(gbt_row["roc_auc"])
            }
except Exception as e_comp:
    print(f"Notice reading comparison table: {e_comp}")

# 5. Output Audit Verification Report
print("\n" + "=" * 85)
print("             BANK COMPLIANCE AUDIT REPORT: MODEL & DATA REPRODUCIBILITY")
print("=" * 85)
print(f"  Delta Table Path         : {FEATURES_PATH}")
print(f"  Audited Version As Of    : Version {target_version}")
print(f"  Dataset Total Records    : {record_count:,}")
print(f"  Reproduced Precision@200 : {reproduced_p200:.4f} ({tp_count}/{total_top200})")
print(f"  Reproduced PR-AUC        : {reproduced_pr_auc:.4f}")
print(f"  Reproduced ROC-AUC       : {reproduced_roc_auc:.4f}")

if logged_metrics:
    diff_p200 = abs(reproduced_p200 - logged_metrics["precision_at_200"])
    diff_pr = abs(reproduced_pr_auc - logged_metrics["pr_auc"])
    print("-" * 85)
    print(f"  Logged Gold P@200        : {logged_metrics['precision_at_200']:.4f} (Delta diff: {diff_p200:.6f})")
    print(f"  Logged Gold PR-AUC       : {logged_metrics['pr_auc']:.4f} (Delta diff: {diff_pr:.6f})")
    is_verified = (diff_p200 < 1e-4) and (diff_pr < 1e-4)
    print(f"  Audit Compliance Status  : {'VERIFIED (100% Deterministic Match)' if is_verified else 'DISCREPANCY DETECTED'}")
print("=" * 85)

spark.stop()
