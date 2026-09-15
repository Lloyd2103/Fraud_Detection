import sys
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import (
    col, count, sum as spark_sum, abs as spark_abs,
    coalesce, lit, when
)
from delta.tables import DeltaTable

SILVER_TRANSACTIONS  = "hdfs:///lakehouse/fraud_detection/silver/transactions"
SILVER_DECISIONS    = "hdfs:///lakehouse/fraud_detection/silver/inspection_decisions"
FEATURES             = "hdfs:///lakehouse/fraud_detection/features"

spark = SparkSession.builder \
    .appName("FraudDetection_PointInTime_FeatureStore") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.debug.maxToStringFields", "200") \
    .config("spark.sql.shuffle.partitions", "100") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("Reading Silver Transactions layer...")
tx_df = spark.read.format("delta").load(SILVER_TRANSACTIONS)

# Feedback loop: merge auditor labels
if DeltaTable.isDeltaTable(spark, SILVER_DECISIONS):
    print(f"Loading auditor feedback labels from {SILVER_DECISIONS}...")
    auditor_df = spark.read.format("delta").load(SILVER_DECISIONS)
    auditor_labels = auditor_df.select(
        col("transaction_id").alias("auditor_tx_id"),
        col("inspection_label").cast("int").alias("auditor_label")
    )

    tx_df = tx_df \
        .join(auditor_labels, tx_df.transaction_id == auditor_labels.auditor_tx_id, "left") \
        .withColumn(
            "is_fraud_label",
            coalesce(col("auditor_label"), col("is_fraud_label").cast("int"))
        ) \
        .drop("auditor_tx_id", "auditor_label")

    print("Auditor feedback labels merged successfully into training dataset.")

# Point-in-Time & Sliding Window Features
print("Configuring Point-in-Time & Sliding Window Functions...")

tx_df = tx_df \
    .withColumn("timestamp", col("timestamp").cast("timestamp")) \
    .withColumn("ts_sec", col("timestamp").cast("long"))

pit_window = Window.partitionBy("source_account").orderBy("ts_sec") \
                   .rangeBetween(Window.unboundedPreceding, -1)
w_24h = Window.partitionBy("source_account").orderBy("ts_sec").rangeBetween(-86400, -1)
w_1h  = Window.partitionBy("source_account").orderBy("ts_sec").rangeBetween(-3600, -1)

error_dest_expr = when(
    col("trans_type").isin("TRANSFER", "PAYMENT"),
    spark_abs((col("old_balance_dest") + col("amount")) - col("new_balance_dest"))
).otherwise(lit(0.0))

tx_with_base_features = tx_df \
    .withColumn("trans_count_total", coalesce(count("transaction_id").over(pit_window), lit(0))) \
    .withColumn("sum_amount_prev",  coalesce(spark_sum("amount").over(pit_window), lit(0.0))) \
    .withColumn("trans_count_24h",  coalesce(count("transaction_id").over(w_24h), lit(0))) \
    .withColumn("sum_amount_24h",   coalesce(spark_sum("amount").over(w_24h), lit(0.0))) \
    .withColumn("trans_count_1h",   coalesce(count("transaction_id").over(w_1h), lit(0)))

feature_store_df = tx_with_base_features \
    .withColumn(
        "avg_amount_prev",
        when(col("trans_count_total") > 0,
             col("sum_amount_prev") / col("trans_count_total"))
        .otherwise(lit(0.0))
    ) \
    .withColumn(
        "amount_to_avg_ratio",
        when(col("avg_amount_prev") > 0,
             col("amount") / col("avg_amount_prev"))
        .otherwise(lit(1.0))
    ) \
    .select(
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
        col("trans_count_24h"),
        col("sum_amount_24h"),
        col("trans_count_1h"),
        spark_abs((col("old_balance_source") - col("amount")) - col("new_balance_source"))
            .alias("error_balance_source"),
        error_dest_expr.alias("error_balance_dest")
    )

print(f"Saving Point-in-Time Feature Store to HDFS: {FEATURES}")
feature_store_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .option("delta.enableChangeDataFeed", "true") \
    .save(FEATURES)

print("Point-in-Time Feature Dataset built successfully.")
spark.stop()