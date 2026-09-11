# Multi-model training and evaluation pipeline for fraud detection
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count, lit, desc, min as spark_min, max as spark_max, current_timestamp, expr
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier, RandomForestClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.functions import vector_to_array

# Khoi tao Spark ML Engine voi cau hinh Delta Lake
spark = SparkSession.builder \
    .appName("FraudDetection_MultiModel_ML_Training") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

features_path = "hdfs:///lakehouse/fraud_detection/features"
candidate_model_save_path = "hdfs:///lakehouse/fraud_detection/models/candidate_gbt_model"
comparison_save_path = "hdfs:///lakehouse/fraud_detection/gold/model_performance_comparison"

VERSION_AS_OF = os.getenv("DELTA_VERSION_AS_OF", None)
TIMESTAMP_AS_OF = os.getenv("DELTA_TIMESTAMP_AS_OF", None)

# Doc dataset kem tinh nang Time Travel neu duoc chi dinh
if VERSION_AS_OF:
    print(f"Loading Point-in-Time Feature Dataset with Time Travel VERSION AS OF {VERSION_AS_OF}...")
    clean_df = spark.read.format("delta").option("versionAsOf", int(VERSION_AS_OF)).load(features_path)
elif TIMESTAMP_AS_OF:
    print(f"Loading Point-in-Time Feature Dataset with Time Travel TIMESTAMP AS OF {TIMESTAMP_AS_OF}...")
    clean_df = spark.read.format("delta").option("timestampAsOf", TIMESTAMP_AS_OF).load(features_path)
else:
    print("Loading Point-in-Time Feature Dataset...")
    clean_df = spark.read.format("delta").load(features_path)

# ==================================================================
# TIME-BASED DATA SPLITTING (DISTRIBUTED PERCENTILE - NO DRIVER OOM)
# ==================================================================
print("Executing Time-based data splitting (70% Train, 15% Val, 15% Test)...")

clean_with_epoch = clean_df.withColumn("ts_numeric", col("timestamp").cast("timestamp").cast("long"))

quantiles = clean_with_epoch.select(
    expr("percentile_approx(ts_numeric, 0.70)").alias("train_cutoff_ts"),
    expr("percentile_approx(ts_numeric, 0.85)").alias("val_cutoff_ts")
).first()

train_cutoff_epoch = quantiles["train_cutoff_ts"]
val_cutoff_epoch = quantiles["val_cutoff_ts"]

train_raw = clean_with_epoch.filter(col("ts_numeric") <= train_cutoff_epoch).drop("ts_numeric")
val_df = clean_with_epoch.filter((col("ts_numeric") > train_cutoff_epoch) & (col("ts_numeric") <= val_cutoff_epoch)).drop("ts_numeric")
test_df = clean_with_epoch.filter(col("ts_numeric") > val_cutoff_epoch).drop("ts_numeric")

train_range = train_raw.select(spark_min("timestamp"), spark_max("timestamp")).first()
val_range = val_df.select(spark_min("timestamp"), spark_max("timestamp")).first()
test_range = test_df.select(spark_min("timestamp"), spark_max("timestamp")).first()

print(f"Train set : {train_raw.count()} records | Time range: [{train_range[0]} -> {train_range[1]}]")
print(f"Val set   : {val_df.count()} records | Time range: [{val_range[0]} -> {val_range[1]}]")
print(f"Test set  : {test_df.count()} records | Time range: [{test_range[0]} -> {test_range[1]}]")

# ==================================================================
# CLASS IMBALANCE HANDLING (UNDERSAMPLING + INVERSE CLASS WEIGHTING)
# ==================================================================
print("Applying Negative Class Undersampling (Ratio 1:20) + Inverse Class Weighting...")
fraud_sample = train_raw.filter(col("is_fraud_label") == 1)
safe_sample = train_raw.filter(col("is_fraud_label") == 0)

fraud_count = fraud_sample.count()
safe_count = safe_sample.count()

sample_fraction = (fraud_count * 20) / safe_count if safe_count > 0 else 1.0
if sample_fraction > 1.0:
    sample_fraction = 1.0

safe_undersampled = safe_sample.sample(False, sample_fraction, seed=42)
train_df = fraud_sample.union(safe_undersampled)

total_train = train_df.count()
fraud_train = train_df.filter(col("is_fraud_label") == 1).count()
safe_train = total_train - fraud_train

fraud_weight = total_train / (2.0 * fraud_train) if fraud_train > 0 else 1.0
safe_weight = total_train / (2.0 * safe_train) if safe_train > 0 else 1.0

train_df = train_df.withColumn("class_weight", when(col("is_fraud_label") == 1, fraud_weight).otherwise(safe_weight))

# ==================================================================
# FEATURE PREPROCESSING PIPELINE
# ==================================================================
type_indexer = StringIndexer(inputCol="trans_type", outputCol="trans_type_idx", handleInvalid="keep")
channel_indexer = StringIndexer(inputCol="channel", outputCol="channel_idx", handleInvalid="keep")

encoder = OneHotEncoder(
    inputCols=["trans_type_idx", "channel_idx"],
    outputCols=["trans_type_vec", "channel_vec"]
)

feature_cols = [
    "amount", "old_balance_source", "new_balance_source", "old_balance_dest", "new_balance_dest",
    "trans_count_total", "sum_amount_prev",
    "error_balance_source", "error_balance_dest", "trans_type_vec", "channel_vec"
]

assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
scaler = StandardScaler(inputCol="raw_features", outputCol="features", withStd=True, withMean=False)

base_stages = [type_indexer, channel_indexer, encoder, assembler, scaler]

# ==================================================================
# MULTI-MODEL COMPARISON CONFIGURATION
# ==================================================================
algorithms = {
    "GBTClassifier": GBTClassifier(
        featuresCol="features",
        labelCol="is_fraud_label",
        weightCol="class_weight",
        maxIter=60,
        maxDepth=6,
        stepSize=0.08,
        subsamplingRate=0.85,
        seed=42
    ),
    "RandomForestClassifier": RandomForestClassifier(
        featuresCol="features",
        labelCol="is_fraud_label",
        weightCol="class_weight",
        numTrees=50,
        maxDepth=5,
        seed=42
    ),
    "LogisticRegression": LogisticRegression(
        featuresCol="features",
        labelCol="is_fraud_label",
        weightCol="class_weight",
        maxIter=50,
        regParam=0.01,
        elasticNetParam=0.5
    )
}

evaluator_roc = BinaryClassificationEvaluator(labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
evaluator_pr = BinaryClassificationEvaluator(labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderPR")

results = []
trained_models = {}
predictions_dict = {}

print("STARTING MULTI-MODEL TRAINING & EVALUATION PIPELINE")

for name, clf in algorithms.items():
    print(f"\n--- Training {name} ---")
    pipeline = Pipeline(stages=base_stages + [clf])
    
    model = pipeline.fit(train_df)
    trained_models[name] = model
    
    predictions = model.transform(test_df)
    predictions_dict[name] = predictions
    
    auc_roc = evaluator_roc.evaluate(predictions)
    auc_pr = evaluator_pr.evaluate(predictions)
    
    pred_with_prob = predictions.withColumn(
        "prob_fraud", vector_to_array(col("probability"))[1]
    )
    
    top200 = pred_with_prob.orderBy(desc("prob_fraud")).limit(200)
    fraud_in_top200 = top200.filter(col("is_fraud_label") == 1).count()
    precision_200 = fraud_in_top200 / 200.0
    
    results.append((name, float(precision_200), float(auc_pr), float(auc_roc), int(fraud_in_top200)))
    print(f"[{name}] Precision@200: {precision_200:.4f} ({fraud_in_top200}/200) | PR-AUC: {auc_pr:.4f} | ROC-AUC: {auc_roc:.4f}")

# IN BANG SO SANH HIEU NANG MO HINH
print("\n" + "="*80)
print(f"{'Algorithm':<25} | {'Precision@200':<15} | {'PR-AUC':<10} | {'ROC-AUC':<10}")
print("="*80)
for r in results:
    print(f"{r[0]:<25} | {r[1]:<15.4f} | {r[2]:<10.4f} | {r[3]:<10.4f}")
print("="*80)

# ==================================================================
# THRESHOLD MOVING EVALUATION (F0.5 SCORE & PR CURVE)
# ==================================================================
print("\n--- Evaluating Decision Thresholds on GBTClassifier (Test Set) ---")
gbt_test_preds = predictions_dict["GBTClassifier"].withColumn(
    "prob_fraud", vector_to_array(col("probability"))[1]
).select("is_fraud_label", "prob_fraud").cache()

thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.85]
print(f"{'Threshold':<12} | {'Precision':<12} | {'Recall':<12} | {'F0.5-Score':<12}")
print("-" * 55)

for th in thresholds:
    th_eval = gbt_test_preds.withColumn("custom_pred", when(col("prob_fraud") >= th, 1.0).otherwise(0.0))
    tp = th_eval.filter((col("custom_pred") == 1) & (col("is_fraud_label") == 1)).count()
    fp = th_eval.filter((col("custom_pred") == 1) & (col("is_fraud_label") == 0)).count()
    fn = th_eval.filter((col("custom_pred") == 0) & (col("is_fraud_label") == 1)).count()
    
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f05 = (1.25 * prec * rec) / (0.25 * prec + rec) if (0.25 * prec + rec) > 0 else 0.0
    print(f"{th:<12.2f} | {prec:<12.4f} | {rec:<12.4f} | {f05:<12.4f}")

gbt_test_preds.unpersist()

# LUU MO HINH UNG VIEN GBTCLASSIFIER XUONG HDFS (KHONG GHI DE PRODUCTION MODEL)
best_model = trained_models["GBTClassifier"]
print(f"\nSaving Candidate GBTClassifier PipelineModel to HDFS: {candidate_model_save_path}...")
best_model.write().overwrite().save(candidate_model_save_path)

# TRICH XUAT FEATURE IMPORTANCE CUA GBT
gbt_stage = best_model.stages[-1]
importances = gbt_stage.featureImportances.toArray()
print("\n--- GBT FEATURE IMPORTANCES ---")
for col_name, imp in zip(feature_cols, importances):
    print(f"Feature: {col_name:<25} | Importance: {imp:.4f}")

# GHI BANG SO SANH HIEU NANG VAO GOLD DELTA TABLE
comparison_rows = [
    (r[0], r[1], r[2], r[3], r[4]) for r in results
]
comp_df = spark.createDataFrame(
    comparison_rows, 
    ["algorithm", "precision_at_200", "pr_auc", "roc_auc", "fraud_detected_in_top200"]
).withColumn("model_role", when(col("algorithm") == "GBTClassifier", lit("candidate")).otherwise(lit("benchmark"))) \
 .withColumn("trained_at", current_timestamp())

comp_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(comparison_save_path)
print(f"Saved model performance comparison matrix to Gold Delta table: {comparison_save_path}")

# GHI TRANG THAI SO SANH PRECISION@200 DE AIRFLOW PHAN NHANH
gbt_precision = [r[1] for r in results if r[0] == "GBTClassifier"][0]
BASELINE_PRECISION = float(os.getenv("BASELINE_PRECISION", "0.85"))

eval_file = "/tmp/model_eval_status"
with open(eval_file, "w") as f:
    if gbt_precision >= BASELINE_PRECISION:
        f.write("better")
        print(f"Decision: Model accepted (Precision@200 {gbt_precision:.4f} >= Baseline {BASELINE_PRECISION:.4f})")
    else:
        f.write("worse")
        print(f"Decision: Model rejected (Precision@200 {gbt_precision:.4f} < Baseline {BASELINE_PRECISION:.4f})")

print("Multi-model training and evaluation pipeline completed successfully.")
spark.stop()