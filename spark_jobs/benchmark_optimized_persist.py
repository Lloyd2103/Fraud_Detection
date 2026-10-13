import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import count, when, col, avg as spark_avg, lit, current_timestamp, to_date

spark = SparkSession.builder.appName("BenchmarkOptimizedPersist") \
    .master("local[4]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.ui.enabled", "false") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

gold_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/gold/risk_scores"
bronze_path = "hdfs://labsoe-17:9000/lakehouse/fraud_detection/bronze"

# Read sample 500 records
df = spark.read.format("delta").load(gold_path).limit(500).cache()
print("Starting optimized persist test...", flush=True)

# 1. Single-pass stats aggregation
t0 = time.time()
stats = df.select(
    count(lit(1)).alias("total_count"),
    count(when(col("inspection_status") == "PENDING", lit(1))).alias("fraud_count"),
    spark_avg("latency_ms").alias("avg_lat")
).collect()[0]
t_stats = time.time() - t0
print(f"1. Single-pass stats: {t_stats*1000:.1f}ms (Total: {stats['total_count']}, Alerts: {stats['fraud_count']})", flush=True)

# 2. Optimized Gold append (coalesce(1), NO mergeSchema)
t0 = time.time()
df.coalesce(1).write.format("delta").mode("append").save(gold_path)
t_gold = time.time() - t0
print(f"2. Optimized Gold append: {t_gold*1000:.1f}ms", flush=True)

# 3. Optimized Bronze append (coalesce(1), NO mergeSchema)
# Prepare bronze sample
bronze_sample = df.withColumn("_ingest_ts", current_timestamp()) \
    .withColumn("_source", lit("kafka:transactions")) \
    .withColumn("_schema_ver", lit("v1.0")) \
    .withColumn("_event_time", col("timestamp")) \
    .withColumn("partition_date", to_date(col("timestamp")))

t0 = time.time()
bronze_sample.coalesce(1).write.format("delta").mode("append").partitionBy("partition_date").save(bronze_path)
t_bronze = time.time() - t0
print(f"3. Optimized Bronze append: {t_bronze*1000:.1f}ms", flush=True)

print(f"TOTAL PERSIST (Gold + Bronze): {(t_gold + t_bronze)*1000:.1f}ms", flush=True)
print(f"TOTAL IF ONLY GOLD: {t_gold*1000:.1f}ms", flush=True)

spark.stop()
