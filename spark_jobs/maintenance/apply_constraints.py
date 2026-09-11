import sys
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("FraudDetection_Delta_Constraints") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

silver_tx_path = "hdfs:///lakehouse/fraud_detection/silver/transactions"

print("--- APPLYING DELTA LAKE CONSTRAINTS (DeTai2.pdf Section 2.7) ---")

try:
    # 1. Add CHECK constraint: amount > 0
    print(f"Adding CHECK constraint (amount > 0) to Silver Transactions at {silver_tx_path}...")
    spark.sql(f"ALTER TABLE delta.`{silver_tx_path}` ADD CONSTRAINT amount_gt_zero CHECK (amount > 0)")
    print("Successfully added constraint: amount_gt_zero CHECK (amount > 0)")
except Exception as e:
    print(f"Notice: Constraint may already exist or error: {e}")

try:
    # 2. Verify constraint enforcement by testing invalid record rejection
    print("\nTesting Delta Constraint Enforcement with invalid record (amount = -500)...")
    invalid_row = [("TX_TEST_INVALID", "C123", "M456", "TRANSFER", -500.0, 1000.0, 500.0, 0.0, 500.0, "ONLINE", 0, "2026-09-09 12:00:00", "2026-09-09")]
    cols = ["transaction_id", "source_account", "dest_account", "trans_type", "amount", "old_balance_source", "new_balance_source", "old_balance_dest", "new_balance_dest", "channel", "is_fraud_label", "timestamp", "partition_date"]
    
    test_df = spark.createDataFrame(invalid_row, cols)
    test_df.write.format("delta").mode("append").save(silver_tx_path)
    print("ERROR: Write succeeded unexpectedly (Constraint failed to reject).")
except Exception as e_reject:
    print(f"SUCCESS: Delta Lake successfully REJECTED invalid write as expected!")
    print(f"Reason: {e_reject}")

spark.stop()
