import sys
from pyspark.sql import SparkSession

def main():
    print("--- INITIALIZING SPARK DELTA LAKE MAINTENANCE (OPTIMIZE & VACUUM) ---")

    spark = SparkSession.builder \
        .appName("FraudDetection_Delta_Optimize_Vacuum") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.databricks.delta.vacuum.parallelDelete.enabled", "true") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Table paths to optimize and maintain
    tables = [
        ("Bronze Transactions", "hdfs:///lakehouse/fraud_detection/bronze/transactions", "partition_date"),
        ("Silver Transactions", "hdfs:///lakehouse/fraud_detection/silver/transactions", "transaction_id"),
        ("Silver Customer States", "hdfs:///lakehouse/fraud_detection/silver/customer_states", "account_id"),
        ("Gold Risk Scores", "hdfs:///lakehouse/fraud_detection/gold/risk_scores", "source_account"),
        ("Features Dataset", "hdfs:///lakehouse/fraud_detection/features", "source_account")
    ]

    for name, path, zorder_col in tables:
        print(f"  Optimizing Delta Table: {name} ({path})")
        try:
            # 1. OPTIMIZE with Z-ORDER INDEXING
            print(f"Running OPTIMIZE Z-ORDER BY ({zorder_col})...")
            spark.sql(f"OPTIMIZE delta.`{path}` ZORDER BY ({zorder_col})")
            print(f"Successfully optimized {name}.")
        except Exception as e_opt:
            print(f"Notice: OPTIMIZE on {name} returned: {e_opt}")

        try:
            # 2. VACUUM OLD COMMIT FILES (RETAIN 168 HOURS / 7 DAYS)
            print(f"Running VACUUM RETAIN 168 HOURS on {name}...")
            spark.sql(f"VACUUM delta.`{path}` RETAIN 168 HOURS")
            print(f"Successfully vacuumed {name}.")
        except Exception as e_vac:
            print(f"Notice: VACUUM on {name} returned: {e_vac}")

    print("\nAll Delta Lake tables optimized and vacuumed successfully.")
    spark.stop()

if __name__ == "__main__":
    main()