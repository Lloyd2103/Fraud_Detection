import os
import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    when,
    count,
    lit,
    desc,
    min as spark_min,
    max as spark_max,
    current_timestamp,
    expr,
    sum as spark_sum,
)
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.classification import (
    GBTClassifier,
    RandomForestClassifier,
    LogisticRegression,
)
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.functions import vector_to_array

start_time = time.time()

from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

FEATURES = os.getenv("FEATURES")
CANDIDATE_PATH = os.getenv("CANDIDATE_PATH")
MODEL_PATH = os.getenv("MODEL_PATH")
STATUS_PATH = os.getenv("STATUS_PATH")
THRESHOLD_PATH = os.getenv("THRESHOLD_PATH", "/lakehouse/fraud_detection/gold/optimal_threshold")
THRESHOLD = float(os.getenv("RISK_THRESHOLD", "0.80"))


spark = (
    SparkSession.builder.appName("ML_Training")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.cleaner.referenceTracking.blocking", "false") \
    .config("spark.cleaner.referenceTracking.blocking.shuffle", "false") \
    .config("spark.cleaner.referenceTracking.cleanBroadcast", "false") \
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

VERSION_AS_OF = os.getenv("DELTA_VERSION_AS_OF", None)
TIMESTAMP_AS_OF = os.getenv("DELTA_TIMESTAMP_AS_OF", None)

if VERSION_AS_OF:
    print(f"Loading with VERSION AS OF {VERSION_AS_OF}...")
    clean_df = (
        spark.read.format("delta")
        .option("versionAsOf", int(VERSION_AS_OF))
        .load(FEATURES)
    )
elif TIMESTAMP_AS_OF:
    print(f"Loading with TIMESTAMP AS OF {TIMESTAMP_AS_OF}...")
    clean_df = (
        spark.read.format("delta")
        .option("timestampAsOf", TIMESTAMP_AS_OF)
        .load(FEATURES)
    )
else:
    clean_df = spark.read.format("delta").load(FEATURES)

print("Executing Time-based data splitting (70% Train, 15% Val, 15% Test)...")

clean_with_epoch = clean_df.withColumn(
    "ts_numeric", col("timestamp").cast("timestamp").cast("long")
).cache()

split_stats = clean_with_epoch.select(
    expr("percentile_approx(ts_numeric, 0.70)").alias("train_cutoff_ts"),
    expr("percentile_approx(ts_numeric, 0.85)").alias("val_cutoff_ts"),
    spark_min("timestamp").alias("min_ts"),
    spark_max("timestamp").alias("max_ts"),
    count("transaction_id").alias("total_rows"),
).first()

train_cutoff_epoch = split_stats["train_cutoff_ts"]
val_cutoff_epoch = split_stats["val_cutoff_ts"]

train_raw = clean_with_epoch.filter(col("ts_numeric") <= train_cutoff_epoch).drop(
    "ts_numeric"
)
val_df = clean_with_epoch.filter(
    (col("ts_numeric") > train_cutoff_epoch) & (col("ts_numeric") <= val_cutoff_epoch)
).drop("ts_numeric")
test_df = (
    clean_with_epoch.filter(col("ts_numeric") > val_cutoff_epoch)
    .drop("ts_numeric")
    .cache()
)
test_count = test_df.count()

print(
    f"Total records: {split_stats['total_rows']} | Time span: [{split_stats['min_ts']} -> {split_stats['max_ts']}]"
)
print(f"Test set: {test_count} records")

# SECTION 2 — CLASS IMBALANCE: ONLY Combined strategy

print(
    "\nBuilding training set with Undersampling strategy (1:10, Natural Probability Calibration)..."
)
train_counts = train_raw.groupBy("is_fraud_label").count().collect()
counts_map = {row["is_fraud_label"]: row["count"] for row in train_counts}
fraud_count = counts_map.get(1, 0)
safe_count = counts_map.get(0, 0)

UNDERSAMPLE_RATIO = float(os.getenv("UNDERSAMPLE_RATIO", "10.0"))
sample_fraction = min(1.0, (fraud_count * UNDERSAMPLE_RATIO) / safe_count) if safe_count > 0 else 1.0

fraud_sample = train_raw.filter(col("is_fraud_label") == 1)
safe_sample = train_raw.filter(col("is_fraud_label") == 0)
safe_undersampled = safe_sample.sample(False, sample_fraction, seed=42)

approx_safe = int(safe_count * sample_fraction)
train_df = fraud_sample.union(safe_undersampled)

print(
    f"  Fraud: {fraud_count:,} | Safe (undersampled 1:{UNDERSAMPLE_RATIO:.0f}): {approx_safe:,} | "
    f"Total Train: {fraud_count + approx_safe:,}"
)


# SECTION 3 — FEATURE PIPELINE

feature_cols = [
    # ---- Core numerics & log (4) ----
    "amount",
    "log_amount",
    "old_balance_source",
    "old_balance_dest",

    # ---- Balance dynamics & Remaining funds (4) ----
    "balance_drain_ratio",
    "remaining_balance_ratio",
    "dest_to_source_bal_ratio",
    "dest_is_merchant",

    # ---- Card Testing & Micro & Structuring (3) ----
    "is_micro_transaction",
    "is_transfer_or_cashout",

    # ---- Window aggregates (5) ----
    "trans_count_1h",
    "trans_count_7d",
    "trans_count_1h_to_7d_ratio",
    "avg_amount_30d",
    "is_unusual_hour",

    # ---- Ratios & Deviations (4) ----
    "amount_to_avg_ratio",
    "amount_to_sum_7d_ratio",
    "amount_zscore_local",
    "amount_diff_avg_30d",

    # ---- Time-since-last & Velocity & Mule (9) ----
    "seconds_since_last_transaction",
    "inbound_count_7d",
    "inbound_amount_7d",
    "inbound_to_outbound_ratio_7d",
    "amount_to_dest_inbound_avg",
    "prev_transaction_amount",
    "amount_ratio_to_prev",
    "is_rapid_fire",
    "is_atm_cashout",

    # ---- Cyclical (1) ----
    "hour_cos",

    # ---- Categoricals (2) — created by StringIndexer in this script ----
    "trans_type_idx",
    "channel_idx",
]

type_indexer = StringIndexer(
    inputCol="trans_type", outputCol="trans_type_idx", handleInvalid="keep"
)
channel_indexer = StringIndexer(
    inputCol="channel", outputCol="channel_idx", handleInvalid="keep"
)
assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
scaler = StandardScaler(
    inputCol="raw_features", outputCol="features", withStd=True, withMean=False
)

print("Fitting Feature Preprocessor Pipeline once...")
preprocessor = Pipeline(stages=[type_indexer, channel_indexer, assembler, scaler]).fit(clean_with_epoch)

train_prep = (
    preprocessor.transform(train_df)
    .select("features", "is_fraud_label")
    .coalesce(6)
    .cache()
)
total_train = train_prep.count()
print(
    f"Train vectors in RAM (6 partitions): {total_train} records (Fraud: {fraud_count})"
)

test_prep = (
    preprocessor.transform(test_df)
    .select("features", "is_fraud_label", "partition_date")
    .cache()
)
test_prep.count()

num_test_days = test_prep.select("partition_date").distinct().count()
test_fraud_count = test_prep.filter(col("is_fraud_label") == 1).count()

print(f"Test days: {num_test_days} | Test frauds: {test_fraud_count}")

clean_with_epoch.unpersist()

# SECTION 4 — MULTI-MODEL TRAINING (3 algorithms × 1 strategy)

algorithms = {
    "GBTClassifier": GBTClassifier(
        featuresCol="features",
        labelCol="is_fraud_label",
        maxIter=25,
        maxDepth=5,
        stepSize=0.12,
        subsamplingRate=0.85,
        seed=42,
    ),
    "RandomForestClassifier": RandomForestClassifier(
        featuresCol="features",
        labelCol="is_fraud_label",
        numTrees=20,
        maxDepth=5,
        seed=42,
    ),
    "LogisticRegression": LogisticRegression(
        featuresCol="features",
        labelCol="is_fraud_label",
        maxIter=20,
    ),
}

trained_models = {}
results = []
gbt_predictions = None

print("\nSTARTING MULTI-MODEL TRAINING")

for name, algo in algorithms.items():
    t0 = time.time()
    print(f"\n--- {name} ---")
    model = algo.fit(train_prep)
    trained_models[name] = model

    predictions = (
        model.transform(test_prep)
        .withColumn("prob_fraud", vector_to_array(col("probability"))[1])
        .cache()
    )
    predictions.count()

    evaluator_pr = BinaryClassificationEvaluator(
        labelCol="is_fraud_label",
        rawPredictionCol="rawPrediction",
        metricName="areaUnderPR",
    )
    evaluator_roc = BinaryClassificationEvaluator(
        labelCol="is_fraud_label",
        rawPredictionCol="rawPrediction",
        metricName="areaUnderROC",
    )

    pr_auc = evaluator_pr.evaluate(predictions)
    roc_auc = evaluator_roc.evaluate(predictions)

    # P@200 per day (threshold-independent — ranking metric)
    daily_top200 = predictions.withColumn(
        "rn",
        row_number().over(
            Window.partitionBy("partition_date").orderBy(desc("prob_fraud"))
        ),
    ).filter(col("rn") <= 200)

    top200_stats = daily_top200.agg(
        count("prob_fraud").alias("total_top200"),
        spark_sum(when(col("is_fraud_label") == 1, 1).otherwise(0)).alias("tp_count"),
    ).first()

    total_top200 = top200_stats["total_top200"] or 0
    tp_count = top200_stats["tp_count"] or 0
    precision_at_200 = tp_count / float(total_top200) if total_top200 > 0 else 0.0

    elapsed = time.time() - t0
    print(
        f"[{name}] Time: {elapsed:.1f}s | Precision@200: {precision_at_200:.4f} "
        f"({tp_count}/{total_top200}) | PR-AUC: {pr_auc:.4f} | ROC-AUC: {roc_auc:.4f}"
    )
    results.append((name, precision_at_200, pr_auc, roc_auc, tp_count))

    if name == "GBTClassifier":
        gbt_predictions = predictions
    else:
        predictions.unpersist()

print("\n" + "=" * 80)
print(f"{'Algorithm':<25} | {'P@200':<10} | {'PR-AUC':<10} | {'ROC-AUC':<10}")
print("=" * 80)
for r in results:
    print(f"{r[0]:<25} | {r[1]:<10.4f} | {r[2]:<10.4f} | {r[3]:<10.4f}")
print("=" * 80)

# SECTION 5 — THRESHOLD EVALUATION (Multi-threshold Calibration Analysis)

print("\n" + "=" * 65)
print(f"{'Threshold':<12} | {'Precision':<12} | {'Recall':<12} | {'F0.5':<12} | {'TP / Total Flagged':<18}")
print("=" * 65)

candidate_thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85]
best_f05 = -1.0
best_th = THRESHOLD
target_prec = 0.0
target_rec = 0.0
target_f05 = 0.0

for th in candidate_thresholds:
    c_stats = gbt_predictions.agg(
        spark_sum(when((col("prob_fraud") >= th) & (col("is_fraud_label") == 1), 1).otherwise(0)).alias("tp"),
        spark_sum(when((col("prob_fraud") >= th) & (col("is_fraud_label") == 0), 1).otherwise(0)).alias("fp"),
        spark_sum(when((col("prob_fraud") < th) & (col("is_fraud_label") == 1), 1).otherwise(0)).alias("fn"),
    ).first()
    c_tp = c_stats["tp"] or 0
    c_fp = c_stats["fp"] or 0
    c_fn = c_stats["fn"] or 0
    c_prec = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
    c_rec = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
    c_f05 = (1.25 * c_prec * c_rec) / (0.25 * c_prec + c_rec) if (0.25 * c_prec + c_rec) > 0 else 0.0
    total_flagged = c_tp + c_fp
    print(f"{th:<12.2f} | {c_prec:<12.4f} | {c_rec:<12.4f} | {c_f05:<12.4f} | {c_tp:,} / {total_flagged:,}")
    if c_f05 > best_f05:
        best_f05 = c_f05
        best_th = th
    if abs(th - THRESHOLD) < 0.01:
        target_prec = c_prec
        target_rec = c_rec
        target_f05 = c_f05

print("=" * 65)
print(f"Optimal Threshold by F0.5: {best_th:.2f} (F0.5 = {best_f05:.4f})")
prec = target_prec
rec = target_rec
f05 = target_f05

# Save threshold to Delta for downstream jobs
threshold_df = spark.createDataFrame(
    [(THRESHOLD, prec, rec, f05, f"evaluated_undersample_1to{int(UNDERSAMPLE_RATIO)}")],
    ["threshold", "precision", "recall", "f0_5", "rationale"],
).withColumn("saved_at", current_timestamp())

threshold_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).save(THRESHOLD_PATH)
print(f"Saved threshold config to {THRESHOLD_PATH}")


gbt_predictions.unpersist()

# SECTION 6 — SAVE PIPELINE MODEL

best_gbt_model = trained_models["GBTClassifier"]
full_pipeline_model = PipelineModel(stages=preprocessor.stages + [best_gbt_model])

print(f"\nSaving full candidate pipeline model to {CANDIDATE_PATH}...")
full_pipeline_model.write().overwrite().save(CANDIDATE_PATH)

importances = best_gbt_model.featureImportances.toArray()
print("\n--- GBT FEATURE IMPORTANCES ---")
zero_features = []
imp_pairs = sorted(
    [
        (feature_cols[i] if i < len(feature_cols) else f"unknown_{i}", imp)
        for i, imp in enumerate(importances)
    ],
    key=lambda x: -x[1],
)
for name, imp in imp_pairs:
    print(f"{name:<32} | {imp:.12f}")
    if imp == 0.0:
        zero_features.append(name)

time_series_features = [
    "trans_count_1h",
    "trans_count_7d",
    "avg_amount_30d",
    "amount_to_avg_ratio",
    "is_unusual_hour",
    "amount_zscore_local",
    "inbound_count_7d",
    "inbound_amount_7d",
]
unused_ts = [f for f in time_series_features if f in zero_features]
if len(unused_ts) == len(time_series_features):
    print(
        f"\n[WARN] All time-series features have importance 0.0. "
        f"This typically means the training dataset has very few repeat-customer events."
    )


# SECTION 7 — PROMOTE DECISION

gbt_precision = [r[1] for r in results if r[0] == "GBTClassifier"][0]
gbt_tp = [r[4] for r in results if r[0] == "GBTClassifier"][0]

max_top_rows = num_test_days * 200
theoretical_max_p200 = (
    min(1.0, test_fraud_count / max_top_rows) if test_fraud_count > 0 else 0.0001
)
normalized_p200 = gbt_precision / theoretical_max_p200
top200_recall = gbt_tp / test_fraud_count if test_fraud_count > 0 else 0.0

print(f"\n--- EVALUATION SUMMARY ---")
print(f"Threshold:                {THRESHOLD}")
print(f"Test Partition Days:      {num_test_days}")
print(f"Test Partition Frauds:    {test_fraud_count}")
print(
    f"Theoretical Max P@200:    {theoretical_max_p200:.4f} ({test_fraud_count}/{max_top_rows})"
)
print(
    f"GBT Precision@200:        {gbt_precision:.4f} (Caught {gbt_tp}/{test_fraud_count} test frauds)"
)
print(f"Top-200 Recall:           {top200_recall:.2%}")
print(f"Normalized P@200:         {normalized_p200:.2%} of theoretical ceiling")
print(f"Precision @ {THRESHOLD}:        {prec:.4f}")
print(f"Recall    @ {THRESHOLD}:        {rec:.4f}")

BASELINE_PRECISION = float(os.getenv("BASELINE_PRECISION", "0.35"))
MIN_RECALL_TOP200 = 0.90

is_promotable = (
    normalized_p200 >= 0.80
    or top200_recall >= MIN_RECALL_TOP200
    or gbt_precision >= BASELINE_PRECISION
)
decision_str = "better" if is_promotable else "worse"

if is_promotable:
    reasons = []
    if normalized_p200 >= 0.80:
        reasons.append(f"Normalized P@200={normalized_p200:.2%} >= 80%")
    if top200_recall >= MIN_RECALL_TOP200:
        reasons.append(f"Top-200 Recall={top200_recall:.2%} >= {MIN_RECALL_TOP200:.0%}")
    if gbt_precision >= BASELINE_PRECISION:
        reasons.append(f"P@200={gbt_precision:.4f} >= baseline {BASELINE_PRECISION}")

    print(f"\nModel ACCEPTED: {' | '.join(reasons)}")
    print(f"Promoting to {MODEL_PATH}...")
    full_pipeline_model.write().overwrite().save(MODEL_PATH)
else:
    print(
        f"\nModel REJECTED (normalized={normalized_p200:.2%}, "
        f"recall={top200_recall:.2%}, raw={gbt_precision:.4f})"
    )

status_df = spark.createDataFrame([(decision_str,)], ["decision"])
status_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).save(STATUS_PATH)

# SECTION 8 — RECORD TO DELTA MODEL REGISTRY (Path A Lineage)
try:
    from datetime import datetime
    from delta.tables import DeltaTable
    from pyspark.sql.types import (
        StructType, StructField, StringType, LongType, DoubleType, IntegerType, TimestampType
    )
    
    REGISTRY_PATH = os.getenv("MODEL_REGISTRY_PATH", "/lakehouse/fraud_detection/models/model_registry")
    GOLD_PATH = os.getenv("GOLD_RISK_SCORES", "/lakehouse/fraud_detection/gold/risk_scores")
    
    v_gold = 0
    if DeltaTable.isDeltaTable(spark, GOLD_PATH):
        hist_g = DeltaTable.forPath(spark, GOLD_PATH).history(1).select("version").collect()
        if hist_g:
            v_gold = int(hist_g[0]["version"])
            
    v_feat = int(VERSION_AS_OF) if VERSION_AS_OF else 0
    if not VERSION_AS_OF and DeltaTable.isDeltaTable(spark, FEATURES):
        hist_f = DeltaTable.forPath(spark, FEATURES).history(1).select("version").collect()
        if hist_f:
            v_feat = int(hist_f[0]["version"])
            
    reg_rows = []
    now_dt = datetime.now()
    for r in results:
        m_name, m_p200, m_pr, m_roc, _ = r
        m_ver = f"{m_name[:3].upper()}_v1.4"
        m_path = MODEL_PATH if (m_name == "GBTClassifier" and is_promotable) else CANDIDATE_PATH
        is_act = 1 if (m_name == "GBTClassifier" and is_promotable) else 0
        m_promo = "better" if (m_name == "GBTClassifier" and is_promotable) else "worse"
        reg_rows.append((
            m_ver, m_name, now_dt, v_gold, v_feat,
            float(m_p200), float(m_pr), float(m_roc),
            str(m_path), m_promo, is_act
        ))
        
    reg_schema = StructType([
        StructField("model_version", StringType(), False),
        StructField("algorithm", StringType(), False),
        StructField("trained_at", TimestampType(), False),
        StructField("gold_risk_scores_version", LongType(), True),
        StructField("features_version", LongType(), True),
        StructField("precision_at_200", DoubleType(), True),
        StructField("pr_auc", DoubleType(), True),
        StructField("roc_auc", DoubleType(), True),
        StructField("model_path", StringType(), True),
        StructField("promotion_decision", StringType(), True),
        StructField("is_active", IntegerType(), True),
    ])
    reg_df = spark.createDataFrame(reg_rows, schema=reg_schema)
    reg_df.write.format("delta").mode("append").save(REGISTRY_PATH)
    print(f"[ModelRegistry] Successfully appended {len(reg_rows)} models to {REGISTRY_PATH}")
except Exception as e_reg:
    print(f"[ModelRegistry] Notice recording to registry: {e_reg}")

train_prep.unpersist()
test_prep.unpersist()

total_duration = time.time() - start_time
print(
    f"\nTotal Job Execution Time: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)"
)
spark.stop()
