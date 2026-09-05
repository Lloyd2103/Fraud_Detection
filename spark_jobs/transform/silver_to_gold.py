import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as spark_sum, round, avg

spark = SparkSession.builder \
    .appName("FraudDetection_SilverToGold_Analytics") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

silver_transactions_path = "hdfs:///lakehouse/fraud_detection/silver/transactions"
gold_summary_path = "hdfs:///lakehouse/fraud_detection/gold/fraud_summary"

print("Reading Silver Transactions layer...")
transactions_df = spark.read.format("delta").load(silver_transactions_path)

print("Generating Gold Fraud Summary Report...")
summary_df = transactions_df.groupBy("trans_type", "channel").agg(
    count("transaction_id").alias("total_transactions"),
    spark_sum("amount").alias("total_volume"),
    spark_sum("is_fraud_label").alias("total_fraud_cases"),
    round(avg("is_fraud_label") * 100, 4).alias("fraud_rate_percentage")
)

print(f"Writing data to Gold Fraud Summary on HDFS: {gold_summary_path}")
summary_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .save(gold_summary_path)

print("Silver to Gold Analytics Transformation executed successfully.")
spark.stop()

