import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, max as spark_max
from delta.tables import DeltaTable

spark = SparkSession.builder \
    .appName("FraudDetection_BronzeToSilver") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

bronze_path = "hdfs:///lakehouse/fraud_detection/bronze"
silver_transactions_path = "hdfs:///lakehouse/fraud_detection/silver/transactions"
silver_states_path = "hdfs:///lakehouse/fraud_detection/silver/customer_states"
quarantine_path = "hdfs:///lakehouse/fraud_detection/_quarantine"

# 1. Read Bronze Delta Table
print("Reading Bronze Delta table...")
bronze_df = spark.read.format("delta").load(bronze_path)

# 2. Filter invalid records for quarantine
invalid_df = bronze_df.filter(
    (col("amount") <= 0) | 
    col("transaction_id").isNull() | 
    col("source_account").isNull() |
    col("dest_account").isNull()
)

if len(invalid_df.take(1)) > 0:
    print("Writing invalid records to quarantine directory...")
    invalid_df.write.format("delta").mode("append").save(quarantine_path)

# 3. Filter valid records and remove duplicates
valid_df = bronze_df.filter(
    (col("amount") > 0) & 
    col("transaction_id").isNotNull() & 
    col("source_account").isNotNull() &
    col("dest_account").isNotNull()
).dropDuplicates(["transaction_id"])

# 4. Save clean data to Silver Transactions layer
print("Saving cleaned transactions to Silver layer...")
valid_df.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("partition_date") \
    .option("overwriteSchema", "true") \
    .save(silver_transactions_path)

# 5. Compute Customer States
print("Computing Customer States...")
from pyspark.sql.functions import sum as spark_sum, avg as spark_avg
customer_states = valid_df.groupBy("source_account").agg(
    count("transaction_id").alias("trans_count_total"),
    spark_sum("amount").alias("total_amount_24h"),
    spark_avg("amount").alias("avg_amount_30d"),
    spark_max("timestamp").alias("last_active_time"),
    spark_max("new_balance_source").alias("last_known_balance")
).withColumnRenamed("source_account", "account_id")


# 6. Execute MERGE / Upsert into Silver Customer States
if DeltaTable.isDeltaTable(spark, silver_states_path):
    print("Executing Delta MERGE into Silver Customer States...")
    try:
        delta_silver = DeltaTable.forPath(spark, silver_states_path)
        delta_silver.alias("target").merge(
            customer_states.alias("source"),
            "target.account_id = source.account_id"
        ).whenMatchedUpdate(set={
            "account_id": "source.account_id",
            "trans_count_total": "source.trans_count_total",
            "total_amount_24h": "source.total_amount_24h",
            "avg_amount_30d": "source.avg_amount_30d",
            "last_active_time": "source.last_active_time",
            "last_known_balance": "source.last_known_balance"
        }).whenNotMatchedInsert(values={
            "account_id": "source.account_id",
            "trans_count_total": "source.trans_count_total",
            "total_amount_24h": "source.total_amount_24h",
            "avg_amount_30d": "source.avg_amount_30d",
            "last_active_time": "source.last_active_time",
            "last_known_balance": "source.last_known_balance"
        }).execute()
    except Exception as e_merge:
        print(f"Notice: Schema variation detected during MERGE ({e_merge}). Overwriting schema...")
        customer_states.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(silver_states_path)
else:
    print("Creating Silver Customer States table for the first time...")
    customer_states.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(silver_states_path)



print("Bronze to Silver ETL pipeline executed successfully.")
spark.stop()

