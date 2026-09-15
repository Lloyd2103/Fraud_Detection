from pyspark.sql import SparkSession

print("--- DEMONSTRATING DELTA LAKE TIME TRAVEL (AUDITABILITY) ---")

spark = SparkSession.builder \
    .appName("FraudDetection_Delta_TimeTravel") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

BRONZE_PATH = "hdfs:///lakehouse/fraud_detection/bronze"

print("1. Reading Bronze Delta Table History...")
try:
    history_df = spark.sql(f"DESCRIBE HISTORY delta.`{BRONZE_PATH}`")
    history_df.select("version", "timestamp", "operation", "operationParameters").show(10, truncate=False)
except Exception as e:
    print(f"Could not retrieve history: {e}")

print("2. Reading Delta Table Version As Of 0...")
try:
    version_zero_df = spark.read.format("delta").option("versionAsOf", 0).load(BRONZE_PATH)
    print(f"Total records in Version 0: {version_zero_df.count()}")
    version_zero_df.show(5)
except Exception as e:
    print(f"Could not read Version 0: {e}")

spark.stop()
