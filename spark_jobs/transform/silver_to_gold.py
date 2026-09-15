import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as spark_sum, round, avg, lit, when

spark = SparkSession.builder \
    .appName("FraudDetection_SilverToGold_Analytics") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

SILVER_TRANSACTIONS = "hdfs:///lakehouse/fraud_detection/silver/transactions"
GOLD_SUMMARY = "hdfs:///lakehouse/fraud_detection/gold/fraud_summary"
GOLD_RISK_SCORES = "hdfs:///lakehouse/fraud_detection/gold/risk_scores"

print("Reading Silver Transactions layer...")
transactions_df = spark.read.format("delta").load(SILVER_TRANSACTIONS)

print("Generating Gold Fraud Summary Report...")
summary_df = transactions_df.groupBy("trans_type", "channel").agg(
    count("transaction_id").alias("total_transactions"),
    spark_sum("amount").alias("total_volume"),
    spark_sum("is_fraud_label").alias("total_fraud_cases"),
    round(avg("is_fraud_label") * 100, 4).alias("fraud_rate_percentage")
)

print(f"Writing data to Gold Fraud Summary on HDFS: {GOLD_SUMMARY}")
summary_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .save(GOLD_SUMMARY)

print("Silver to Gold Transformations executed successfully (gold.fraud_summary updated).")
spark.stop()


