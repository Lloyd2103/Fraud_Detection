import os
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, coalesce, current_timestamp, to_timestamp, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, DateType
)

# Spark session
print("--- INITIALIZING SPARK STRUCTURED STREAMING (STANDALONE MODE) ---")

spark = SparkSession.builder \
    .appName("FraudDetection_BronzeIngestion") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.databricks.delta.optimizeWrite.enabled", "true") \
    .config("spark.databricks.delta.autoCompact.enabled", "true") \
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
    .config("spark.sql.adaptive.enabled", "false") \
    .config("spark.network.timeout", "600s") \
    .config("spark.executor.heartbeatInterval", "60s") \
    .config("spark.hadoop.dfs.client.socket-timeout", "180000") \
    .config("spark.hadoop.dfs.datanode.socket.write.timeout", "180000") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Suppress Netty transport shutdown noise
try:
    log4j = spark._jvm.org.apache.log4j
    for noisy in [
        "org.apache.spark.network.client.TransportResponseHandler",
        "org.apache.spark.network.server.TransportChannelHandler",
        "org.apache.spark.ContextCleaner",
    ]:
        log4j.Logger.getLogger(noisy).setLevel(log4j.Level.OFF)
except Exception:
    pass


# Schema
schema = StructType([
    StructField("transaction_id",     StringType(),  False),
    StructField("source_account",     StringType(),  True),
    StructField("dest_account",       StringType(),  True),
    StructField("trans_type",         StringType(),  True),
    StructField("amount",             DoubleType(),  True),
    StructField("old_balance_source", DoubleType(),  True),
    StructField("new_balance_source", DoubleType(),  True),
    StructField("old_balance_dest",   DoubleType(),  True),
    StructField("new_balance_dest",   DoubleType(),  True),
    StructField("channel",            StringType(),  True),
    StructField("timestamp",          StringType(),  True),
    StructField("received_at",        StringType(),  True),
    StructField("partition_date",     StringType(),  True),
])

# Configuration
MASTER_IP = os.getenv("MASTER_IP", "192.168.80.200")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{MASTER_IP}:9092")
KAFKA_TOPIC             = os.getenv("KAFKA_TOPIC", "transactions")

BRONZE_PATH         = os.getenv("BRONZE_PATH", "hdfs:///lakehouse/fraud_detection/bronze")
CHECKPOINT_PATH     = os.getenv("CHECKPOINT_BRONZE_INGEST") or os.getenv("CHECKPOINT_PATH", "hdfs:///lakehouse/fraud_detection/checkpoints/bronze_ingest")

TRIGGER_MODE = os.getenv("TRIGGER_MODE", "processingTime").lower()
TRIGGER_INTERVAL = os.getenv("TRIGGER_INTERVAL", "30 seconds")
MAX_OFFSETS_PER_TRIGGER = os.getenv("MAX_OFFSETS_PER_TRIGGER", "20000")

print(f"--- KAFKA BROKER:      {KAFKA_BOOTSTRAP_SERVERS} ---")
print(f"--- KAFKA TOPIC:       {KAFKA_TOPIC} ---")
print(f"--- BRONZE PATH:       {BRONZE_PATH} ---")
print(f"--- CHECKPOINT:        {CHECKPOINT_PATH} ---")
print(f"--- TRIGGER MODE:      {TRIGGER_MODE} ---")
if TRIGGER_MODE == "processingtime":
    print(f"--- TRIGGER INTERVAL:  {TRIGGER_INTERVAL} ---")
print(f"--- MAX OFFSETS/BATCH: {MAX_OFFSETS_PER_TRIGGER} ---")


# Read stream
kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", os.getenv("STARTING_OFFSETS", "latest")) \
    .option("failOnDataLoss", "false") \
    .option("kafka.request.timeout.ms", "180000") \
    .option("kafka.default.api.timeout.ms", "180000") \
    .option("maxOffsetsPerTrigger", MAX_OFFSETS_PER_TRIGGER) \
    .load()

# Parse + enrich
parsed_stream_df = kafka_stream_df \
    .selectExpr("CAST(value AS STRING) AS json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*")

bronze_df = parsed_stream_df \
    .withColumn("_ingest_ts", current_timestamp()) \
    .withColumn("_source", lit("kafka:transactions")) \
    .withColumn("_schema_ver", lit("v1.0")) \
    .withColumn(
        "_event_time",
        coalesce(
            to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"),
            current_timestamp(),
        ),
    ) \
    .withColumn("partition_date", col("_event_time").cast(DateType()))

# Write stream
print(f"--- STREAMING TO BRONZE DELTA: {BRONZE_PATH} ---")

builder = bronze_df.writeStream \
    .queryName("Bronze_Kafka_Ingestion") \
    .format("delta") \
    .outputMode("append") \
    .partitionBy("partition_date") \
    .option("checkpointLocation", CHECKPOINT_PATH) \
    .option("mergeSchema", "true")

if TRIGGER_MODE == "availablenow":
    print("--- MODE: availableNow (one-shot backfill) ---", flush=True)
    query = builder.trigger(availableNow=True).start(BRONZE_PATH)
else:
    print(f"--- MODE: processingTime({TRIGGER_INTERVAL}) (continuous) ---", flush=True)
    query = builder.trigger(processingTime=TRIGGER_INTERVAL).start(BRONZE_PATH)

print(">>> Bronze Streaming Query is ACTIVE and running...", flush=True)
query.awaitTermination()