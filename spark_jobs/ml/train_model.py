# Multi-model training and evaluation pipeline for fraud detection
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count, lit, desc, min as spark_min, max as spark_max, current_timestamp, expr
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier, RandomForestClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.functions import vector_to_array

FEATURES = "hdfs:///lakehouse/fraud_detection/features"
CANDIDATE_PATH = "hdfs:///lakehouse/fraud_detection/models/candidate_gbt_model"
MODEL_PATH = "hdfs:///lakehouse/fraud_detection/models/gbt_fraud_model"
COMPARISON_PATH = "hdfs:///lakehouse/fraud_detection/gold/model_performance_comparison"
STATUS_PATH = "hdfs:///lakehouse/fraud_detection/models/_eval_status"

spark = SparkSession.builder \
    .appName("FraudDetection_MultiModel_ML_Training") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

VERSION_AS_OF = os.getenv("DELTA_VERSION_AS_OF", None)
TIMESTAMP_AS_OF = os.getenv("DELTA_TIMESTAMP_AS_OF", None)

if VERSION_AS_OF:
    print(f"Loading with VERSION AS OF {VERSION_AS_OF}...")
    clean_df = spark.read.format("delta").option("versionAsOf", int(VERSION_AS_OF)).load(FEATURES)
elif TIMESTAMP_AS_OF:
    print(f"Loading with TIMESTAMP AS OF {TIMESTAMP_AS_OF}...")
    clean_df = spark.read.format("delta").option("timestampAsOf", TIMESTAMP_AS_OF).load(FEATURES)
else:
    clean_df = spark.read.format("delta").load(FEATURES)

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

train_range = train_raw.agg(spark_min("timestamp").alias("start"), spark_max("timestamp").alias("end")).first()
val_range = val_df.agg(spark_min("timestamp").alias("start"), spark_max("timestamp").alias("end")).first()
test_range = test_df.agg(spark_min("timestamp").alias("start"), spark_max("timestamp").alias("end")).first()

print(f"Train set : {train_raw.count()} records | Time range: [{train_range[0]} -> {train_range[1]}]")
print(f"Val set   : {val_df.count()} records | Time range: [{val_range[0]} -> {val_range[1]}]")
print(f"Test set  : {test_df.count()} records | Time range: [{test_range[0]} -> {test_range[1]}]")

# CLASS IMBALANCE: Undersampling 1:20 + inverse weight
print("Undersampling 1:20 + inverse class weight...")
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

# FEATURE PIPELINE
type_indexer = StringIndexer(inputCol="trans_type", outputCol="trans_type_idx", handleInvalid="keep")

feature_cols = [
    "amount",
    "old_balance_source",
    "new_balance_source",
    "old_balance_dest",
    "new_balance_dest",
    "trans_count_total",
    "sum_amount_prev",
    "trans_count_24h",
    "sum_amount_24h",
    "trans_count_1h",
    "error_balance_source",
    "error_balance_dest",
    "trans_type_idx",
]

assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
scaler = StandardScaler(inputCol="raw_features", outputCol="features", withStd=True, withMean=False)

base_stages = [type_indexer, assembler, scaler]

# MODELS
algorithms = {
    "GBTClassifier": GBTClassifier(
        featuresCol="features", labelCol="is_fraud_label", weightCol="class_weight",
        maxIter=60, maxDepth=6, stepSize=0.08, subsamplingRate=0.85, seed=42
    ),
    "RandomForestClassifier": RandomForestClassifier(
        featuresCol="features", labelCol="is_fraud_label", weightCol="class_weight",
        numTrees=30, maxDepth=6, seed=42
    ),
    "LogisticRegression": LogisticRegression(
        featuresCol="features", labelCol="is_fraud_label", weightCol="class_weight",
        maxIter=30
    )
}

trained_models = {}
results = []
predictions_dict = {}

print("\nSTARTING MULTI-MODEL TRAINING")

for name, algo in algorithms.items():
    print(f"\n--- {name} ---")
    pipeline = Pipeline(stages=base_stages + [algo])
    model = pipeline.fit(train_df)
    trained_models[name] = model

    predictions = model.transform(test_df)
    predictions_dict[name] = predictions

    evaluator_pr = BinaryClassificationEvaluator(
        labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderPR"
    )
    evaluator_roc = BinaryClassificationEvaluator(
        labelCol="is_fraud_label", rawPredictionCol="rawPrediction", metricName="areaUnderROC"
    )

    pr_auc = evaluator_pr.evaluate(predictions)
    roc_auc = evaluator_roc.evaluate(predictions)

    daily_top200 = predictions \
        .withColumn("prob_fraud", vector_to_array(col("probability"))[1]) \
        .withColumn("rn", row_number().over(Window.partitionBy("partition_date").orderBy(desc("prob_fraud")))) \
        .filter(col("rn") <= 200)

    total_top200 = daily_top200.count()
    tp_count = daily_top200.filter(col("is_fraud_label") == 1).count()
    precision_at_200 = tp_count / float(total_top200) if total_top200 > 0 else 0.0

    print(f"[{name}] Precision@200: {precision_at_200:.4f} ({tp_count}/{total_top200}) | PR-AUC: {pr_auc:.4f} | ROC-AUC: {roc_auc:.4f}")
    results.append((name, precision_at_200, pr_auc, roc_auc, tp_count))

print("\n" + "=" * 80)
print(f"{'Algorithm':<25} | {'P@200':<10} | {'PR-AUC':<10} | {'ROC-AUC':<10}")
print("=" * 80)
for r in results:
    print(f"{r[0]:<25} | {r[1]:<10.4f} | {r[2]:<10.4f} | {r[3]:<10.4f}")
print("=" * 80)

# THRESHOLD SWEEP
print("\n--- Threshold sweep on GBT ---")
gbt_test_preds = predictions_dict["GBTClassifier"].withColumn(
    "prob_fraud", vector_to_array(col("probability"))[1]
).select("is_fraud_label", "prob_fraud").cache()

thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.85]
print(f"{'Threshold':<12} | {'Precision':<12} | {'Recall':<12} | {'F0.5':<12}")
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

# SAVE MODELS
best_model = trained_models["GBTClassifier"]
print(f"\nSaving candidate to {CANDIDATE_PATH}...")
best_model.write().overwrite().save(CANDIDATE_PATH)

# FEATURE IMPORTANCE (1-1 mapping, KHÔNG expand)
gbt_stage = best_model.stages[-1]
importances = gbt_stage.featureImportances.toArray()

print("\n--- GBT FEATURE IMPORTANCES ---")
for i, imp in enumerate(importances):
    name = feature_cols[i] if i < len(feature_cols) else f"unknown_{i}"
    print(f"{name:<30} | {imp:.4f}")

# PROMOTE DECISION
gbt_precision = [r[1] for r in results if r[0] == "GBTClassifier"][0]
BASELINE_PRECISION = float(os.getenv("BASELINE_PRECISION", "0.35"))
decision_str = "better" if gbt_precision >= BASELINE_PRECISION else "worse"

if decision_str == "better":
    print(f"\nModel ACCEPTED (P@200 {gbt_precision:.4f} >= {BASELINE_PRECISION:.4f})")
    print(f"Promoting to {MODEL_PATH}...")
    best_model.write().overwrite().save(MODEL_PATH)
else:
    print(f"\nModel REJECTED (P@200 {gbt_precision:.4f} < {BASELINE_PRECISION:.4f})")

# WRITE COMPARISON + STATUS
comparison_rows = [(r[0], r[1], r[2], r[3], r[4], decision_str) for r in results]
comp_df = spark.createDataFrame(
    comparison_rows,
    ["algorithm", "precision_at_200", "pr_auc", "roc_auc", "fraud_detected_in_top200", "promotion_decision"]
).withColumn("model_role", when(col("algorithm") == "GBTClassifier", lit("candidate")).otherwise(lit("benchmark"))) \
 .withColumn("trained_at", current_timestamp())

comp_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(COMPARISON_PATH)
print(f"Saved comparison to {COMPARISON_PATH}")

status_df = spark.createDataFrame([(decision_str,)], ["decision"])
status_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(STATUS_PATH)

print("Done.")
spark.stop()