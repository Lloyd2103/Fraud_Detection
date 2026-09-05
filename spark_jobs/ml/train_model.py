import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count, lit, desc, min, max, current_timestamp
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier, RandomForestClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.functions import vector_to_array

# INITIALIZE SPARK ML ENGINE
spark = SparkSession.builder \
    .appName("FraudDetection_MultiModel_ML_Training") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

features_path = "hdfs:///lakehouse/fraud_detection/features"
model_save_path = "hdfs:///lakehouse/fraud_detection/models/gbt_fraud_model"
comparison_save_path = "hdfs:///lakehouse/fraud_detection/gold/model_performance_comparison"

print("Loading Point-in-Time Feature Dataset...")
clean_df = spark.read.format("delta").load(features_path)

# ==================================================================
# TIME-BASED DATA SPLITTING (PREVENT FUTURE DATA LEAKAGE)
# Strict 70% Train, 15% Validation, 15% Test based on transaction timestamp
# ==================================================================
print("Executing Time-based data splitting (70% Train, 15% Val, 15% Test)...")
total_count = clean_df.count()
train_cutoff = int(total_count * 0.70)
val_cutoff = int(total_count * 0.85)

timestamps = clean_df.select("timestamp").orderBy("timestamp").collect()
train_ts = timestamps[train_cutoff - 1][0]
val_ts = timestamps[val_cutoff - 1][0]

train_raw = clean_df.filter(col("timestamp") <= train_ts)
val_df = clean_df.filter((col("timestamp") > train_ts) & (col("timestamp") <= val_ts))
test_df = clean_df.filter(col("timestamp") > val_ts)

print(f"Train set: {train_raw.count()} records | Val set: {val_df.count()} records | Test set: {test_df.count()} records")

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
    "trans_count_total", "error_balance_source", "error_balance_dest", "trans_type_vec", "channel_vec"
]

assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
scaler = StandardScaler(inputCol="raw_features", outputCol="features", withStd=True, withMean=False)

base_stages = [type_indexer, channel_indexer, encoder, assembler, scaler]

# ==================================================================
# MULTI-MODEL COMPARISON (GBT, RANDOM FOREST, LOGISTIC REGRESSION)
# ==================================================================
algorithms = {
    "GBTClassifier": GBTClassifier(
        featuresCol="features",
        labelCol="is_fraud_label",
        weightCol="class_weight",
        maxIter=50,
        maxDepth=5,
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

print("\n" + "="*80)
print("STARTING MULTI-MODEL TRAINING & EVALUATION PIPELINE")
print("="*80)

for name, clf in algorithms.items():
    print(f"\n--- Training {name} ---")
    pipeline = Pipeline(stages=base_stages + [clf])
    model = pipeline.fit(train_df)
    trained_models[name] = model
    
    predictions = model.transform(test_df)
    
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

# PRINT COMPARISON SUMMARY TABLE
print("\n" + "="*80)
print(f"{'Algorithm':<25} | {'Precision@200':<15} | {'PR-AUC':<10} | {'ROC-AUC':<10}")
print("="*80)
for r in results:
    print(f"{r[0]:<25} | {r[1]:<15.4f} | {r[2]:<10.4f} | {r[3]:<10.4f}")
print("="*80)

# SAVE PRIMARY MODEL (GBT) AND COMPARISON RESULTS TO DELTA LAKE
best_model = trained_models["GBTClassifier"]

print(f"\nSaving GBT PipelineModel to HDFS: {model_save_path}...")
best_model.write().overwrite().save(model_save_path)

# EXTRACT FEATURE IMPORTANCES FOR GBT MODEL
gbt_stage = best_model.stages[-1]
importances = gbt_stage.featureImportances.toArray()
print("\n--- GBT FEATURE IMPORTANCES ---")
for col_name, imp in zip(feature_cols, importances):
    print(f"Feature: {col_name:<25} | Importance: {imp:.4f}")

# Write comparison table to Gold Delta Table
comparison_rows = [
    (r[0], r[1], r[2], r[3], r[4]) for r in results
]
comp_df = spark.createDataFrame(comparison_rows, ["algorithm", "precision_at_200", "pr_auc", "roc_auc", "fraud_detected_in_top200"]) \
    .withColumn("trained_at", current_timestamp())

comp_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(comparison_save_path)
print(f"Saved model performance comparison matrix to Gold Delta table: {comparison_save_path}")

print("Multi-model training and evaluation pipeline completed successfully.")
spark.stop()