import os
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

import time
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, max as spark_max
from delta.tables import DeltaTable
from datetime import datetime, timedelta

parser = argparse.ArgumentParser(description="Delta Lake maintenance (OPTIMIZE + VACUUM)")
parser.add_argument("--benchmark", action="store_true",
                    help="Đo query latency trước/sau OPTIMIZE (DeTai2 Section 2.7)")
parser.add_argument("--retain-hours", type=int, default=168,
                    help="Vacuum retention (giờ). Default 168 (7 ngày).")
args = parser.parse_args()

spark = (
    SparkSession.builder.appName("FraudDetection_Delta_Maintenance")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.databricks.delta.vacuum.parallelDelete.enabled", "true")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

BRONZE_PATH            = os.getenv("BRONZE_PATH", "hdfs:///lakehouse/fraud_detection/bronze")
SILVER_TRANSACTIONS    = os.getenv("SILVER_TRANSACTIONS", "hdfs:///lakehouse/fraud_detection/silver/transactions")
SILVER_CUSTOMER_STATES = os.getenv("SILVER_CUSTOMER_STATES", "hdfs:///lakehouse/fraud_detection/silver/customer_states")
GOLD_RISK_SCORES       = os.getenv("GOLD_RISK_SCORES", "hdfs:///lakehouse/fraud_detection/gold/risk_scores")
FEATURES               = os.getenv("FEATURES", "hdfs:///lakehouse/fraud_detection/features")

BENCH_ACCOUNT = None
BENCH_CUTOFF = None


def discover_bench_target():
    global BENCH_ACCOUNT, BENCH_CUTOFF
    silver_df = spark.read.format("delta").load(SILVER_TRANSACTIONS)
    max_ts = silver_df.select(spark_max("timestamp")).collect()[0][0]
    if not max_ts:
        return False
    max_dt = datetime.strptime(str(max_ts)[:19], "%Y-%m-%d %H:%M:%S")
    BENCH_CUTOFF = (max_dt - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    sample = (
        silver_df.filter(col("source_account").startswith("C") & (col("timestamp") >= BENCH_CUTOFF))
        .groupBy("source_account").count()
        .filter((col("count") >= 5) & (col("count") <= 50))
        .limit(1).collect()
    )
    if not sample:
        return False
    BENCH_ACCOUNT = sample[0]["source_account"]
    print(f"[BENCH] Auto-discovered account: {BENCH_ACCOUNT}")
    print(f"[BENCH] 30-day window cutoff   : {BENCH_CUTOFF}")
    return True


def run_benchmark():
    sql = f"""
        SELECT count(*) AS n, coalesce(sum(amount), 0.0) AS amt
        FROM delta.`{SILVER_TRANSACTIONS}`
        WHERE source_account = '{BENCH_ACCOUNT}' AND timestamp >= '{BENCH_CUTOFF}'
    """
    t0 = time.time()
    r = spark.sql(sql).collect()[0]
    return (time.time() - t0) * 1000.0, int(r["n"]), float(r["amt"])


print("=" * 80)
print(f"--- DELTA LAKE MAINTENANCE (OPTIMIZE + VACUUM RETAIN {args.retain_hours}H) ---")
print("--- MODE: WITH BENCHMARK ---" if args.benchmark else "--- MODE: MAINTENANCE ONLY ---")
print("=" * 80)

pre_latency = None
if args.benchmark:
    if discover_bench_target():
        pre_latency, pre_n, pre_amt = run_benchmark()
        print(f"[BENCH-PRE ] {pre_latency:.1f} ms  (rows={pre_n}, amount={pre_amt:,.2f})")
    else:
        print("[BENCH] WARNING: could not discover benchmark account, skipping benchmark")
        args.benchmark = False

tables = [
    ("Bronze Transactions",    BRONZE_PATH,            None),
    ("Silver Transactions",    SILVER_TRANSACTIONS,    "source_account, timestamp"),
    ("Silver Customer States", SILVER_CUSTOMER_STATES, "account_id"),
    ("Gold Risk Scores",       GOLD_RISK_SCORES,       "source_account, timestamp"),
    ("Features Dataset",       FEATURES,               "source_account, timestamp"),
]

for name, path, zcols in tables:
    print(f"\n>> Processing Delta Table: {name} ({path})")

    if not DeltaTable.isDeltaTable(spark, path):
        print(f"   Notice: Table does not exist. Skipping.")
        continue

    try:
        t0 = time.time()
        if zcols:
            cols = [c.strip() for c in zcols.split(",")]
            escaped_cols = ", ".join(f"`{c}`" for c in cols)
            print(f"   Executing: OPTIMIZE ZORDER BY ({escaped_cols})...")
            spark.sql(f"OPTIMIZE delta.`{path}` ZORDER BY ({escaped_cols})")
        else:
            print(f"   Executing: OPTIMIZE (coalesce small files)...")
            spark.sql(f"OPTIMIZE delta.`{path}`")
        print(f"   Successfully optimized {name}. ({time.time()-t0:.1f}s)")

        t0 = time.time()
        print(f"   Executing: VACUUM RETAIN {args.retain_hours} HOURS...")
        spark.sql(f"VACUUM delta.`{path}` RETAIN {args.retain_hours} HOURS")
        print(f"   Successfully vacuumed {name}. ({time.time()-t0:.1f}s)")

    except Exception as e_tbl:
        print(f"   Maintenance FAILED for {name}: {e_tbl}")

if args.benchmark and pre_latency is not None:
    print()
    post_latency, post_n, post_amt = run_benchmark()
    print(f"[BENCH-POST] {post_latency:.1f} ms  (rows={post_n}, amount={post_amt:,.2f})")
    speedup = pre_latency / post_latency if post_latency > 0 else 0.0
    print("=" * 80)
    print("[BENCHMARK RESULT — DeTai2 Section 2.7]")
    print(f"  Account                : {BENCH_ACCOUNT}")
    print(f"  30-day cutoff          : {BENCH_CUTOFF}")
    print(f"  Latency BEFORE         : {pre_latency:.2f} ms")
    print(f"  Latency AFTER          : {post_latency:.2f} ms")
    print(f"  Speedup                : {speedup:.2f}x")
    print("=" * 80)


# DESCRIBE HISTORY + VERSION SNAPSHOTS

print()
print("=" * 80)
print("--- DESCRIBE HISTORY (3 versions gần nhất mỗi bảng) ---")
print("=" * 80)
for name, path, _ in tables:
    if not DeltaTable.isDeltaTable(spark, path):
        continue
    try:
        print(f"\n--- {name} ---")
        spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 3") \
            .select("version", "timestamp", "operation", "operationParameters") \
            .show(truncate=False)
        latest = spark.sql(f"DESCRIBE HISTORY delta.`{path}` LIMIT 1").collect()[0]
        v = latest["version"]
        n = spark.read.format("delta").load(path).count()
        print(f"  Latest version : {v}")
        print(f"  Row count      : {n:,}")
        print(f"  Demo command   : SELECT count(*) FROM delta.`{path}` VERSION AS OF {v};")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n--- DELTA LAKE MAINTENANCE COMPLETED SUCCESSFULLY ---")
spark.stop()