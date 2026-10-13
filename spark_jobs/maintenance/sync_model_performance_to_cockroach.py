"""
Sync Model Performance & Drift Monitoring from Delta Lake Gold to CockroachDB
Reads:
  - hdfs://labsoe-17:9000/lakehouse/fraud_detection/gold/model_performance_comparison
  - hdfs://labsoe-17:9000/lakehouse/fraud_detection/gold/drift_monitoring
Writes:
  - CockroachDB: model_performance (UPSERT ON CONFLICT algorithm)
  - CockroachDB: model_drift (UPSERT / MERGE by date + feature_name)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv
from pyspark.sql import SparkSession

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

HDFS_HOST = os.getenv("HDFS_HOST", "hdfs://labsoe-17:9000")
GOLD_PERF_PATH = f"{HDFS_HOST}/lakehouse/fraud_detection/gold/model_performance_comparison"
GOLD_DRIFT_PATH = f"{HDFS_HOST}/lakehouse/fraud_detection/gold/drift_monitoring"

DB_HOST = os.getenv("DB_HOST", "192.168.80.201")
DB_PORT = os.getenv("DB_PORT", "26257")
DB_NAME = os.getenv("DB_NAME", "system_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123")


def get_spark_session():
    return (
        SparkSession.builder.appName("SyncModelPerformanceToCockroach")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .master("local[2]")
        .getOrCreate()
    )


def sync_metrics():
    print("=" * 65)
    print("  SYNC DELTA GOLD MODEL PERFORMANCE & DRIFT TO COCKROACHDB")
    print("=" * 65)
    print(f"HDFS Perf Table:  {GOLD_PERF_PATH}")
    print(f"HDFS Drift Table: {GOLD_DRIFT_PATH}")
    print(f"CockroachDB:      {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("-" * 65)

    spark = get_spark_session()
    spark.sparkContext.setLogLevel("ERROR")

    # 1. Connect to CockroachDB
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )
    conn.autocommit = True
    cur = conn.cursor()

    # 2. Read & Sync model_performance_comparison
    try:
        print("[INFO] Reading Delta Gold model_performance_comparison...")
        perf_df = spark.read.format("delta").load(GOLD_PERF_PATH)
        perf_rows = perf_df.collect()
        print(f"[INFO] Found {len(perf_rows)} models in Delta Gold table.")

        upsert_perf_sql = """
        INSERT INTO model_performance (
            algorithm, precision_at_200, pr_auc, roc_auc, fraud_detected_in_top200,
            promotion_decision, model_role, trained_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (algorithm) DO UPDATE SET
            precision_at_200 = EXCLUDED.precision_at_200,
            pr_auc = EXCLUDED.pr_auc,
            roc_auc = EXCLUDED.roc_auc,
            fraud_detected_in_top200 = EXCLUDED.fraud_detected_in_top200,
            promotion_decision = EXCLUDED.promotion_decision,
            model_role = EXCLUDED.model_role,
            trained_at = EXCLUDED.trained_at;
        """

        synced_perf_count = 0
        for r in perf_rows:
            d = r.asDict()
            algo = d.get("algorithm")
            p200 = float(d.get("precision_at_200") or 0.0)
            pr_auc = float(d.get("pr_auc") or 0.0)
            roc_auc = float(d.get("roc_auc") or 0.0)
            fraud_tp = int(d.get("fraud_detected_in_top200") or 0)
            decision = str(d.get("promotion_decision") or "better")
            role = str(d.get("model_role") or "candidate")
            trained_at = d.get("trained_at")

            cur.execute(
                upsert_perf_sql,
                (algo, p200, pr_auc, roc_auc, fraud_tp, decision, role, trained_at),
            )
            synced_perf_count += 1
            print(f"  ✓ Upserted {algo}: P@200={p200:.3f}, PR_AUC={pr_auc:.3f}, ROC_AUC={roc_auc:.3f}, Role={role}")

        print(f"[SUCCESS] Synced {synced_perf_count} model performance records to CockroachDB.")
    except Exception as e:
        print(f"[ERROR] Failed to sync model_performance: {e}")

    # 3. Read & Sync drift_monitoring
    try:
        print("\n[INFO] Reading Delta Gold drift_monitoring...")
        drift_df = spark.read.format("delta").load(GOLD_DRIFT_PATH)
        drift_rows = drift_df.collect()
        print(f"[INFO] Found {len(drift_rows)} drift records in Delta Gold table.")

        synced_drift_count = 0
        for r in drift_rows:
            d = r.asDict()
            dt_str = str(d.get("date") or "")
            feat = str(d.get("feature_name") or "")
            psi = float(d.get("psi") or 0.0)
            ks = float(d.get("ks_statistic") or 0.0)
            drift_lvl = str(d.get("drift_level") or "stable")

            # Check if record for (date, feature_name) already exists
            cur.execute(
                "SELECT id FROM model_drift WHERE date = %s AND feature_name = %s LIMIT 1;",
                (dt_str, feat),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE model_drift 
                    SET psi = %s, ks_statistic = %s, drift_level = %s 
                    WHERE id = %s;
                    """,
                    (psi, ks, drift_lvl, existing[0]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO model_drift (date, feature_name, psi, ks_statistic, drift_level)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (dt_str, feat, psi, ks, drift_lvl),
                )
            synced_drift_count += 1

        print(f"[SUCCESS] Synced {synced_drift_count} drift monitoring records to CockroachDB.")
    except Exception as e:
        print(f"[ERROR] Failed to sync drift_monitoring: {e}")

    cur.close()
    conn.close()
    spark.stop()
    print("\n[COMPLETE] Sync completed successfully.")


if __name__ == "__main__":
    sync_metrics()
