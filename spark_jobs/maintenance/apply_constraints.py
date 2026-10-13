import os
import sys
from datetime import datetime
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
)

spark = SparkSession.builder \
    .appName("FraudDetection_Delta_Constraints") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

SILVER_TRANSACTIONS = os.getenv("SILVER_TRANSACTIONS")
GOLD_RISK_SCORES    = os.getenv("GOLD_RISK_SCORES")


try:
    print("=== APPLYING DELTA LAKE CONSTRAINTS & CONFIGURATIONS ===")
    
    # 1. Add CHECK constraint: amount > 0 (Silver Transactions)
    print(f"\n[1/3] Processing Silver Transactions at: {SILVER_TRANSACTIONS}")
    
    # Bước 1.1: Xóa dữ liệu lỗi lịch sử (nếu có) để tránh vỡ constraint khi ALTER TABLE
    print("  -> Cleaning invalid historical records (amount < 0 or negative balances)...")
    try:
        spark.sql(f"""
            DELETE FROM delta.`{SILVER_TRANSACTIONS}` 
            WHERE amount < 0 OR old_balance_source < 0 OR new_balance_source < 0
        """)
    except Exception as e_clean:
        print(f"  ! Notice on Silver cleaning: {e_clean}")

    # 1.2. Add CHECK constraint: amount > 0
    print("  -> Adding CHECK constraint: amount_gt_zero (amount >= 0)...")
    try:
        spark.sql(f"ALTER TABLE delta.`{SILVER_TRANSACTIONS}` ADD CONSTRAINT amount_gt_zero CHECK (amount >= 0)")
        print("  ✓ Successfully added constraint: amount_gt_zero")
    except Exception as e:
        if "exist" in str(e).lower() or "already" in str(e).lower():
            print("  ! Notice: Constraint 'amount_gt_zero' already exists.")
        else:
            print(f"  ! Warning on Silver constraint: {e}")

    # 1.4. Add CHECK constraint: valid_trans_type
    print("  -> Adding CHECK constraint: valid_trans_type...")
    try:
        spark.sql(f"""
            ALTER TABLE delta.`{SILVER_TRANSACTIONS}` 
            ADD CONSTRAINT valid_trans_type 
            CHECK (trans_type IN ('PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN'))
        """)
        print("  ✓ Successfully added constraint: valid_trans_type")
    except Exception as e:
        if "exist" in str(e).lower() or "already" in str(e).lower():
            print("  ! Notice: Constraint 'valid_trans_type' already exists.")
        else:
            print(f"  ! Warning on trans_type constraint: {e}")

    # 2. Add business constraint & enable CDF on Gold Risk Scores
    print(f"\n[2/3] Processing Gold Risk Scores at: {GOLD_RISK_SCORES}")
    
    # Bước 2.1: Dọn dẹp dữ liệu vi phạm cũ ở tầng Gold
    try:
        spark.sql(f"DELETE FROM delta.`{GOLD_RISK_SCORES}` WHERE risk_score < 0.0 OR risk_score > 1.0")
    except Exception as e_gold_clean:
        print(f"  ! Notice on Gold cleaning: {e_gold_clean}")

    # Bước 2.2: Thêm Constraint risk_score trong khoảng [0.0, 1.0]
    print("  -> Adding CHECK constraint: risk_score_range (0.0 <= risk_score <= 1.0)...")
    try:
        spark.sql(f"ALTER TABLE delta.`{GOLD_RISK_SCORES}` ADD CONSTRAINT risk_score_range CHECK (risk_score >= 0.0 AND risk_score <= 1.0)")
        print("  ✓ Successfully added constraint: risk_score_range")
    except Exception as e:
        if "exist" in str(e).lower() or "already" in str(e).lower():
            print("  ! Notice: Constraint 'risk_score_range' already exists.")
        else:
            print(f"  ! Warning on Gold constraint: {e}")

    # Bước 2.3: Bật Change Data Feed (CDF)
    print("  -> Enabling Change Data Feed (CDF)...")
    try:
        spark.sql(f"ALTER TABLE delta.`{GOLD_RISK_SCORES}` SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        print("  ✓ Successfully enabled Change Data Feed (CDF)")
    except Exception as e:
        print(f"  ! Warning on CDF enable: {e}")

    # 3. Verify constraint enforcement with invalid record (amount = -500.0)
    print("\n[3/3] Testing Delta Constraint Enforcement with invalid record (amount = -500)...")
    
    schema = StructType([
        StructField("transaction_id", StringType(), True),
        StructField("source_account", StringType(), True),
        StructField("dest_account", StringType(), True),
        StructField("trans_type", StringType(), True),
        StructField("amount", DoubleType(), True),
        StructField("old_balance_source", DoubleType(), True),
        StructField("new_balance_source", DoubleType(), True),
        StructField("old_balance_dest", DoubleType(), True),
        StructField("new_balance_dest", DoubleType(), True),
        StructField("channel", StringType(), True),
        StructField("is_fraud_label", IntegerType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("partition_date", StringType(), True)
    ])

    invalid_row = [(
        "TX_TEST_INVALID", "C123", "M456", "TRANSFER", 
        -500.0, 1000.0, 500.0, 0.0, 500.0, 
        "ONLINE", 0, datetime.strptime("2026-09-09 12:00:00", "%Y-%m-%d %H:%M:%S"), "2026-09-09"
    )]

    test_df = spark.createDataFrame(invalid_row, schema=schema)

    try:
        test_df.write.format("delta").mode("append").save(SILVER_TRANSACTIONS)
        print("  ❌ CRITICAL ERROR: Write succeeded unexpectedly! (Constraint failed to enforce)")
    except Exception as e_reject:
        print("  ✓ VERIFICATION SUCCESS: Delta Lake REJECTED the invalid write as expected!")
        print(f"  -> Exception Detail: {e_reject}")

finally:
    print("\nStopping SparkSession...")
    spark.stop()