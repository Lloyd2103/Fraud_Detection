import sys
from pyspark.sql import SparkSession

print("--- STARTING DELTA LAKE OPTIMIZATION & MAINTENANCE (DAG 4: gl_bao_tri) ---")

spark = SparkSession.builder \
    .appName("FraudDetection_Delta_Optimize_Vacuum") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

tables_to_optimize = [
    ("hdfs:///lakehouse/fraud_detection/silver/transactions", "source_account, timestamp"),
    ("hdfs:///lakehouse/fraud_detection/silver/customer_states", "account_id"),
    ("hdfs:///lakehouse/fraud_detection/features", "source_account, timestamp")
]

for table_path, zorder_cols in tables_to_optimize:
    try:
        print(f"Optimizing table at {table_path} with Z-ORDER BY ({zorder_cols})...")
        spark.sql(f"OPTIMIZE delta.`{table_path}` ZORDER BY ({zorder_cols})")
        print(f"Running VACUUM RETAIN 168 HOURS on table {table_path}...")
        spark.sql(f"VACUUM delta.`{table_path}` RETAIN 168 HOURS")
        print(f"Successfully maintained table: {table_path}")
    except Exception as e:
        print(f"Notice during optimization of {table_path}: {e}")

print("Maintenance job completed.")
spark.stop()
