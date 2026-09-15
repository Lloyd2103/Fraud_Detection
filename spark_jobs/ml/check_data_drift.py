import sys
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, to_timestamp
from delta.tables import DeltaTable

FEATURES = "hdfs:///lakehouse/fraud_detection/features"
DRIFT_GOLD    = "hdfs:///lakehouse/fraud_detection/gold/drift_monitoring"
STATUS_PATH   = "hdfs:///lakehouse/fraud_detection/models/_drift_status"

spark = SparkSession.builder \
    .appName("FraudDetection_PSI_KS_Drift_Monitoring") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

NUM_BINS = 10

FEATURES_TO_CHECK = [
    "amount", "old_balance_source", "new_balance_source",
    "old_balance_dest", "new_balance_dest",
    "trans_count_total", "sum_amount_prev", "amount_to_avg_ratio",
    "trans_count_24h", "sum_amount_24h", "trans_count_1h",
    "error_balance_source", "error_balance_dest",
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

    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    print(f"Baseline: partition_date < {seven_days_ago}")
    print(f"Target  : partition_date >= {seven_days_ago}")

    baseline_df = all_features.filter(col("partition_date") < seven_days_ago)
    target_df   = all_features.filter(col("partition_date") >= seven_days_ago)

    n_base = baseline_df.count()
    n_target = target_df.count()
    print(f"Baseline rows: {n_base} | Target rows: {n_target}")

    if n_base < MIN_BASELINE_ROWS or n_target < MIN_TARGET_ROWS:
        msg = f"Insufficient data (baseline={n_base}, target={n_target}). Skipping drift."
        print(msg)
        write_status("unknown", msg)
        spark.stop()
        return 

    baseline_df.cache()
    target_df.cache()

    today_str = datetime.now().strftime("%Y-%m-%d")
    results = []
    max_psi = 0.0
    skipped = []

    for f in FEATURES_TO_CHECK:
        if f not in baseline_df.columns or f not in target_df.columns:
            skipped.append(f)
            print(f"SKIP {f}: không có trong features schema")
            continue

        base_clean = baseline_df.select(f).dropna()
        target_clean = target_df.select(f).dropna()

        result = compute_drift_for_feature(base_clean, target_clean, f)
        if result is None:
            skipped.append(f)
            print(f"SKIP {f}: không đủ dữ liệu để tính quantile")
            continue

        feature, psi, ks, level = result
        max_psi = max(max_psi, psi)
        results.append((today_str, feature, psi, ks, level))
        print(f"{feature:<25} | PSI: {psi:.4f} | KS: {ks:.4f} | {level}")

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