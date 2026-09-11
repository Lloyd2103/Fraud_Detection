import sys
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import col, count, sum as spark_sum, abs as spark_abs, coalesce, lit, when
from delta.tables import DeltaTable

spark = SparkSession.builder \
    .appName("FraudDetection_PointInTime_FeatureStore") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.debug.maxToStringFields", "200") \
    .config("spark.sql.shuffle.partitions", "100") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

silver_transactions_path = "hdfs:///lakehouse/fraud_detection/silver/transactions"
inspection_decisions_path = "hdfs:///lakehouse/fraud_detection/silver/inspection_decisions"
features_save_path = "hdfs:///lakehouse/fraud_detection/features"

print("Reading Silver Transactions layer...")
tx_df = spark.read.format("delta").load(silver_transactions_path)

# Feedback Loop: Merge auditor inspection labels if available
if DeltaTable.isDeltaTable(spark, inspection_decisions_path):
    print(f"Loading auditor feedback labels from {inspection_decisions_path}...")
    auditor_df = spark.read.format("delta").load(inspection_decisions_path)
    auditor_labels = auditor_df.select(
        col("transaction_id").alias("auditor_tx_id"),
        col("inspection_label").alias("auditor_label")
    )
    tx_df = tx_df.join(auditor_labels, tx_df.transaction_id == auditor_labels.auditor_tx_id, "left") \
                 .withColumn("final_label", coalesce(col("auditor_label"), col("is_fraud_label"))) \
                 .drop("auditor_tx_id", "auditor_label", "is_fraud_label") \
                 .withColumnRenamed("final_label", "is_fraud_label")
    print("Auditor feedback labels merged successfully into training dataset.")

print("Configuring Point-in-Time Window Function...")
pit_window = Window.partitionBy("source_account") \
                    .orderBy("timestamp") \
                    .rowsBetween(Window.unboundedPreceding, -1)


error_dest_expr = when(
    col("trans_type").isin("TRANSFER", "PAYMENT"),
    spark_abs((col("old_balance_dest") + col("amount")) - col("new_balance_dest"))
).otherwise(lit(0.0))

tx_with_base_features = tx_df.withColumn(
    "trans_count_total", coalesce(count("transaction_id").over(pit_window), lit(0))
).withColumn(
    "sum_amount_prev", coalesce(spark_sum("amount").over(pit_window), lit(0.0))
)

feature_store_df = tx_with_base_features.withColumn(
    "avg_amount_prev",
    when(col("trans_count_total") > 0, col("sum_amount_prev") / col("trans_count_total")).otherwise(lit(0.0))
).withColumn(
    "amount_to_avg_ratio",
    when(col("avg_amount_prev") > 0, col("amount") / col("avg_amount_prev")).otherwise(lit(1.0))
).select(
    col("transaction_id"),
    col("source_account"),
    col("dest_account"),
    col("trans_type"),
    col("amount"),
    col("old_balance_source"),
    col("new_balance_source"),
    col("old_balance_dest"),
    col("new_balance_dest"),
    col("channel"),
    col("is_fraud_label"),
    col("timestamp"),
    col("partition_date"),
    col("trans_count_total"),
    col("sum_amount_prev"),
    col("avg_amount_prev"),
    col("amount_to_avg_ratio"),
    spark_abs((col("old_balance_source") - col("amount")) - col("new_balance_source")).alias("error_balance_source"),
    error_dest_expr.alias("error_balance_dest")
)

print(f"Saving Point-in-Time Feature Store to HDFS: {features_save_path}")
feature_store_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .option("delta.enableChangeDataFeed", "true") \
    .save(features_save_path)

print("Point-in-Time Feature Dataset built successfully.")
spark.stop()