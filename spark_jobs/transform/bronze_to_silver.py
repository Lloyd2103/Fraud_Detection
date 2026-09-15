from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, max as spark_max, sum as spark_sum,
    avg as spark_avg, stddev as spark_stddev, countDistinct,
    hour, collect_set, slice, sort_array, struct, current_timestamp
)
from delta.tables import DeltaTable

spark = SparkSession.builder \
    .appName("FraudDetection_BronzeToSilver") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

BRONZE_PATH         = "hdfs:///lakehouse/fraud_detection/bronze"
SILVER_TRANSACTIONS = "hdfs:///lakehouse/fraud_detection/silver/transactions"
SILVER_STATES       = "hdfs:///lakehouse/fraud_detection/silver/customer_states"
QUARANTINE_PATH     = "hdfs:///lakehouse/fraud_detection/_quarantine"

bronze_df = spark.read.format("delta").load(BRONZE_PATH)

invalid_df = bronze_df.filter(
    (col("amount") <= 0) |
    col("transaction_id").isNull() |
    col("source_account").isNull() |
    col("dest_account").isNull()
)

if invalid_df.take(1):
    invalid_df.write.format("delta").mode("append").save(QUARANTINE_PATH)

valid_df = bronze_df.filter(
    (col("amount") > 0) &
    col("transaction_id").isNotNull() &
    col("source_account").isNotNull() &
    col("dest_account").isNotNull()
).dropDuplicates(["transaction_id"])

valid_df.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("partition_date") \
    .option("overwriteSchema", "true") \
    .save(SILVER_TRANSACTIONS)

# Customer states snapshot
customer_states = valid_df.groupBy("source_account").agg(
    count("transaction_id").alias("trans_count_total"),
    spark_sum("amount").alias("sum_amount_history"),
    spark_avg("amount").alias("avg_amount_history"),
    spark_stddev("amount").alias("stddev_amount_history"),
    countDistinct("dest_account").alias("unique_dest_accounts"),
    spark_max("timestamp").alias("last_active_time"),
    spark_max("new_balance_source").alias("last_known_balance")
).withColumnRenamed("source_account", "account_id")

hourly = valid_df \
    .withColumn("tx_hour", hour(col("timestamp"))) \
    .groupBy("source_account", "tx_hour") \
    .agg(count("transaction_id").alias("c"))

frequent_hours = hourly \
    .groupBy("source_account") \
    .agg(
        slice(
            sort_array(
                collect_set(struct(col("c").alias("cnt"), col("tx_hour").alias("hr"))),
                asc=False
            ), 1, 3
        ).alias("top_hours_struct")
    ) \
    .select(
        col("source_account").alias("account_id"),
        col("top_hours_struct.hr").alias("frequent_tx_hours")
    )

customer_states = customer_states \
    .join(frequent_hours, "account_id", "left") \
    .withColumn("tx_count_1h",  col("trans_count_total")) \
    .withColumn("tx_count_24h", col("trans_count_total")) \
    .withColumn("tx_count_7d",  col("trans_count_total")) \
    .withColumn("total_amount_24h", col("sum_amount_history")) \
    .withColumn("updated_at", current_timestamp())

if DeltaTable.isDeltaTable(spark, SILVER_STATES):
    DeltaTable.forPath(spark, SILVER_STATES).alias("t").merge(
        customer_states.alias("s"), "t.account_id = s.account_id"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    customer_states.write.format("delta").mode("overwrite") \
        .option("overwriteSchema", "true").save(SILVER_STATES)

print("Bronze to Silver done.")
spark.stop()