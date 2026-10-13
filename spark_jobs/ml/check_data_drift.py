import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, to_timestamp, max as spark_max
from delta.tables import DeltaTable

def clean_path(p):
    if p and p.startswith("hdfs:///"):
        return "/" + p[len("hdfs:///"):].lstrip("/")
    return p

FEATURES    = clean_path(os.getenv("FEATURES", "/lakehouse/fraud_detection/features"))
DRIFT_GOLD  = clean_path(os.getenv("DRIFT_GOLD", "/lakehouse/fraud_detection/gold/drift_monitoring"))
STATUS_PATH = clean_path(os.getenv("DRIFT_STATUS_PATH", "/lakehouse/fraud_detection/gold/drift_status"))


spark = SparkSession.builder \
    .appName("FraudDetection_PSI_KS_Drift_Monitoring") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

NUM_BINS = 10

# 18 actual numeric features in Point-in-Time Feature Store (DeTai2.pdf Section 2.5 & 2.6)
FEATURES_TO_CHECK = [
    "amount", "log_amount", "old_balance_source", "old_balance_dest",
    "balance_drain_ratio", "remaining_balance_ratio", "dest_to_source_bal_ratio",
    "trans_count_1h", "trans_count_7d", "avg_amount_30d",
    "amount_to_avg_ratio", "amount_to_sum_7d_ratio", "amount_zscore_local",
    "amount_diff_avg_30d", "seconds_since_last_transaction",
    "inbound_count_7d", "inbound_amount_7d", "amount_ratio_to_prev"
]

MIN_BASELINE_ROWS = 1000
MIN_TARGET_ROWS   = 100

def compute_psi(base_counts, target_counts, n_base, n_target):
    import math
    psi = 0.0
    for b_c, t_c in zip(base_counts, target_counts):
        b_pct = max(b_c / float(n_base), 0.0001)
        t_pct = max(t_c / float(n_target), 0.0001)
        psi += (t_pct - b_pct) * math.log(t_pct / b_pct)
    return psi


def compute_ks_from_counts(base_counts, target_counts, n_base, n_target):
    max_ks = 0.0
    cum_b, cum_t = 0, 0
    for i in range(len(base_counts)):
        cum_b += base_counts[i]
        cum_t += target_counts[i]
        ks = abs(cum_b / float(n_base) - cum_t / float(n_target))
        if ks > max_ks:
            max_ks = ks
    return max_ks


def calculate_psi_and_ks(base_data, target_data, num_buckets=10):
    import numpy as np
    quantiles = np.percentile(base_data, np.linspace(0, 100, num_buckets + 1))
    quantiles = sorted(list(set(quantiles)))
    if len(quantiles) < 2:
        return 0.0, 0.0
    base_counts = np.histogram(base_data, bins=quantiles)[0].tolist()
    target_counts = np.histogram(target_data, bins=quantiles)[0].tolist()
    psi = compute_psi(base_counts, target_counts, len(base_data), len(target_data))
    ks = compute_ks_from_counts(base_counts, target_counts, len(base_data), len(target_data))
    return psi, ks

def bucketize(df, feature, quantiles):
    expr = when(col(feature).isNull(), lit(-1))
    expr = expr.when(col(feature) <= lit(quantiles[0]), lit(0))
    for i in range(1, len(quantiles)):
        expr = expr.when(col(feature) <= lit(quantiles[i]), lit(i))
    return df.withColumn("bucket", expr.otherwise(lit(len(quantiles))))


def compute_drift_for_feature(baseline_df, target_df, feature):
    probs = [i / float(NUM_BINS) for i in range(1, NUM_BINS)]
    quantiles = baseline_df.approxQuantile(feature, probs, 0.01)
    if not quantiles or len(quantiles) < 2:
        return None

    base_rows = bucketize(baseline_df, feature, quantiles) \
        .filter(col("bucket") >= 0).groupBy("bucket").count().collect()
    targ_rows = bucketize(target_df, feature, quantiles) \
        .filter(col("bucket") >= 0).groupBy("bucket").count().collect()

    base_map = {r["bucket"]: r["count"] for r in base_rows}
    targ_map = {r["bucket"]: r["count"] for r in targ_rows}
    n_buckets = len(quantiles) + 1

    base_counts = [base_map.get(i, 0) for i in range(n_buckets)]
    targ_counts = [targ_map.get(i, 0) for i in range(n_buckets)]
    n_base = sum(base_counts)
    n_target = sum(targ_counts)

    if n_base == 0 or n_target == 0:
        return None

    psi = compute_psi(base_counts, targ_counts, n_base, n_target)
    ks = compute_ks_from_counts(base_counts, targ_counts, n_base, n_target)

    if psi < 0.1:
        level = "stable"
    elif psi <= 0.25:
        level = "warning"
    else:
        level = "critical"

    return (feature, float(psi), float(ks), level)


def write_status(status, note=""):
    today = datetime.now().strftime("%Y-%m-%d")
    df = spark.createDataFrame([(status, note, today)], ["status", "note", "updated_date"])
    df.write.format("delta").mode("overwrite") \
        .option("overwriteSchema", "true").save(STATUS_PATH)


def main():
    print("--- DATA DRIFT MONITORING (PSI + KS) ---")

    all_features = spark.read.format("delta").load(FEATURES)

    # Dynamic target window based on max partition_date in feature dataset
    max_date_row = all_features.select(spark_max("partition_date")).collect()[0]
    max_date_val = max_date_row[0]
    if max_date_val is None:
        max_date = datetime.now().date()
    elif isinstance(max_date_val, str):
        max_date = datetime.strptime(max_date_val, "%Y-%m-%d").date()
    else:
        max_date = max_date_val

    cutoff_date = (max_date - timedelta(days=7)).strftime("%Y-%m-%d")
    max_date_formatted = max_date.strftime("%Y-%m-%d")

    print(f"Dataset Latest Partition Date : {max_date_formatted}")
    print(f"Baseline Window (Historical)  : partition_date < {cutoff_date}")
    print(f"Target Window (Recent 7-Day)  : partition_date >= {cutoff_date} AND partition_date <= {max_date_formatted}")

    baseline_df = all_features.filter(col("partition_date") < cutoff_date)
    target_df   = all_features.filter((col("partition_date") >= cutoff_date) & (col("partition_date") <= max_date_formatted))

    n_base = baseline_df.count()
    n_target = target_df.count()
    print(f"Baseline rows: {n_base:,} | Target rows: {n_target:,}")

    if n_base < MIN_BASELINE_ROWS or n_target < MIN_TARGET_ROWS:
        msg = f"Insufficient data (baseline={n_base}, target={n_target}). Skipping drift."
        print(msg)
        write_status("unknown", msg)
        spark.stop()
        return 

    baseline_df.cache()
    target_df.cache()

    today_str = max_date_formatted
    results = []
    max_psi = 0.0
    skipped = []

    valid_features = [f for f in FEATURES_TO_CHECK if f in baseline_df.columns and f in target_df.columns]
    for f in FEATURES_TO_CHECK:
        if f not in valid_features:
            skipped.append(f)
            print(f"SKIP {f}: không có trong features schema")

    # High-performance representative sampling for vectorized PSI & KS calculation
    sample_size = 50000
    base_frac = min(1.0, float(sample_size) / float(n_base))
    target_frac = min(1.0, float(sample_size) / float(n_target))

    print(f"\nSampling {base_frac*100:.1f}% baseline and {target_frac*100:.1f}% target data for vectorized drift evaluation...")
    base_pdf = baseline_df.select(valid_features).sample(fraction=base_frac, seed=42).toPandas()
    targ_pdf = target_df.select(valid_features).sample(fraction=target_frac, seed=42).toPandas()
    print(f"Loaded into memory: {len(base_pdf):,} baseline rows, {len(targ_pdf):,} target rows.\n")

    print("-" * 65)
    print(f"{'Feature':<30} | {'PSI':<7} | {'KS':<7} | {'Drift Level'}")
    print("-" * 65)

    for f in valid_features:
        base_clean = base_pdf[f].dropna().values
        target_clean = targ_pdf[f].dropna().values

        if len(base_clean) < MIN_TARGET_ROWS or len(target_clean) < MIN_TARGET_ROWS:
            skipped.append(f)
            print(f"SKIP {f}: không đủ dữ liệu")
            continue

        psi, ks = calculate_psi_and_ks(base_clean, target_clean, num_buckets=NUM_BINS)

        if psi < 0.1:
            level = "stable"
        elif psi <= 0.25:
            level = "warning"
        else:
            level = "critical"

        max_psi = max(max_psi, psi)
        results.append((today_str, f, float(psi), float(ks), level))
        print(f"{f:<30} | {psi:<7.4f} | {ks:<7.4f} | {level}")

    if not results:
        msg = f"No features computed. Skipped: {skipped}"
        print(msg)
        write_status("unknown", msg)
        baseline_df.unpersist()
        target_df.unpersist()
        spark.stop()
        return

    drift_df = spark.createDataFrame(
        results, ["date", "feature_name", "psi", "ks_statistic", "drift_level"]
    )

    if DeltaTable.isDeltaTable(spark, DRIFT_GOLD):
        drift_df.write.format("delta").mode("append").save(DRIFT_GOLD)
    else:
        drift_df.write.format("delta").mode("overwrite") \
            .option("overwriteSchema", "true").save(DRIFT_GOLD)

    print(f"Ghi drift metrics vào {DRIFT_GOLD}")

    if max_psi > 0.25:
        status = "critical"
    elif max_psi >= 0.1:
        status = "warning"
    else:
        status = "stable"

    write_status(status, f"max_psi={max_psi:.4f}, computed={len(results)} features")
    print(f"Drift status: {status} (max PSI = {max_psi:.4f})")

    baseline_df.unpersist()
    target_df.unpersist()
    spark.stop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        try:
            write_status("error", str(e)[:200])
        except Exception:
            pass
        sys.exit(1)