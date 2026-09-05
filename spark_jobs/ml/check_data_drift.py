import sys
import math
import bisect
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit
from delta.tables import DeltaTable

def calculate_psi_and_ks(baseline_vals, target_vals, num_bins=10):
    """Compute Population Stability Index (PSI) and KS-Statistic efficiently in O(N log N)."""
    if not baseline_vals or not target_vals:
        return 0.0, 0.0
    
    n_base = len(baseline_vals)
    n_target = len(target_vals)
    
    sorted_base = sorted(baseline_vals)
    sorted_target = sorted(target_vals)
    
    percentiles = [i / float(num_bins) for i in range(1, num_bins)]
    bins = [-float('inf')]
    for p in percentiles:
        idx = min(int(p * n_base), n_base - 1)
        bins.append(sorted_base[idx])
    bins.append(float('inf'))
    
    bins = sorted(list(set(bins)))
    if len(bins) < 2:
        return 0.0, 0.0
        
    base_counts = [0] * (len(bins) - 1)
    for v in baseline_vals:
        for i in range(len(bins) - 1):
            if bins[i] <= v < bins[i+1]:
                base_counts[i] += 1
                break
                
    target_counts = [0] * (len(bins) - 1)
    for v in target_vals:
        for i in range(len(bins) - 1):
            if bins[i] <= v < bins[i+1]:
                target_counts[i] += 1
                break
                
    psi = 0.0
    for b_c, t_c in zip(base_counts, target_counts):
        b_pct = max(b_c / float(n_base), 0.0001)
        t_pct = max(t_c / float(n_target), 0.0001)
        psi += (t_pct - b_pct) * math.log(t_pct / b_pct)
        
    # Efficient O(N log N) KS-statistic calculation via bisect
    all_vals = sorted(list(set(sorted_base + sorted_target)))
    if len(all_vals) > 2000:
        step = len(all_vals) // 2000
        sampled_points = all_vals[::step]
    else:
        sampled_points = all_vals

    max_ks = 0.0
    for val in sampled_points:
        cdf_b = bisect.bisect_right(sorted_base, val) / float(n_base)
        cdf_t = bisect.bisect_right(sorted_target, val) / float(n_target)
        ks = abs(cdf_b - cdf_t)
        if ks > max_ks:
            max_ks = ks
            
    return float(psi), float(max_ks)

def run_drift_monitoring():
    print("--- INITIALIZING DATA DRIFT MONITORING ENGINE (PSI & KS STATISTIC) ---")

    spark = SparkSession.builder \
        .appName("FraudDetection_PSI_KS_Drift_Monitoring") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    baseline_features_path = "hdfs:///lakehouse/fraud_detection/features"
    target_transactions_path = "hdfs:///lakehouse/fraud_detection/silver/transactions"
    drift_gold_path = "hdfs:///lakehouse/fraud_detection/gold/drift_monitoring"

    try:
        print(f"Reading Baseline Features from {baseline_features_path}...")
        baseline_df = spark.read.format("delta").load(baseline_features_path)
        
        print(f"Reading Target Transactions from {target_transactions_path}...")
        target_df = spark.read.format("delta").load(target_transactions_path)
        
        features_to_check = ["amount", "old_balance_source", "trans_count_total"]
        results = []
        max_overall_psi = 0.0
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for f in features_to_check:
            if f in baseline_df.columns and f in target_df.columns:
                print(f"Computing PSI & KS for feature: {f}...")
                base_vals = [r[0] for r in baseline_df.select(f).dropna().limit(10000).collect() if r[0] is not None]
                targ_vals = [r[0] for r in target_df.select(f).dropna().limit(10000).collect() if r[0] is not None]
                
                psi, ks = calculate_psi_and_ks(base_vals, targ_vals)

                
                if psi < 0.1:
                    level = "stable"
                elif psi <= 0.25:
                    level = "warning"
                else:
                    level = "critical"
                    
                if psi > max_overall_psi:
                    max_overall_psi = psi
                    
                results.append((today_str, f, float(psi), float(ks), level))
                print(f"Feature: {f:<20} | PSI: {psi:.4f} | KS: {ks:.4f} | Level: {level}")
                
        drift_df = spark.createDataFrame(results, ["date", "feature_name", "psi", "ks_statistic", "drift_level"])
        
        if DeltaTable.isDeltaTable(spark, drift_gold_path):
            drift_df.write.format("delta").mode("append").save(drift_gold_path)
        else:
            drift_df.write.format("delta").mode("overwrite").save(drift_gold_path)
            
        print(f"Drift monitoring metrics written to Gold table: {drift_gold_path}")
        
        if max_overall_psi > 0.25:
            status = "critical"
        elif max_overall_psi >= 0.1:
            status = "warning"
        else:
            status = "stable"
            
        with open("/tmp/drift_status", "w") as f:
            f.write(status)
        print(f"Overall Drift Status written to /tmp/drift_status: {status}")

    except Exception as e:
        print(f"Error during drift calculation: {str(e)}")
        with open("/tmp/drift_status", "w") as f:
            f.write("error")
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    run_drift_monitoring()



