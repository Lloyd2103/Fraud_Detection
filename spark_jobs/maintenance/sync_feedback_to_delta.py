import os
import json
import time
from dotenv import load_dotenv

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from delta.tables import DeltaTable
from kafka import KafkaConsumer

GOLD_RISK_SCORES = os.getenv("GOLD_RISK_SCORES", "hdfs:///lakehouse/fraud_detection/gold/risk_scores")
SILVER_DECISIONS = os.getenv("SILVER_DECISIONS", "hdfs:///lakehouse/fraud_detection/silver/inspection_decisions")
KAFKA_BROKERS    = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.200:9092,127.0.0.1:9092")
FEEDBACK_TOPIC   = "auditor_feedback"
CONSUMER_GROUP   = "sync_feedback_to_delta"

print("--- DELTA LAKE MERGE: FEEDBACK LOOP CDC TO DELTA GOLD & SILVER ---")
print(f"Target Gold:   {GOLD_RISK_SCORES}")
print(f"Target Silver: {SILVER_DECISIONS}")


# 1. Poll Kafka 'auditor_feedback'
brokers = [b.strip() for b in KAFKA_BROKERS.split(",")]
consumer = KafkaConsumer(
    bootstrap_servers=brokers,
    group_id=CONSUMER_GROUP,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    consumer_timeout_ms=30000,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)
consumer.subscribe([FEEDBACK_TOPIC])

print(f"Connecting to Kafka {brokers} topic '{FEEDBACK_TOPIC}' (group={CONSUMER_GROUP})...")

raw_records = []

def process_message(msg):
    val = msg.value
    if not val or not isinstance(val, dict):
        return
    if val.get("op") == "d":
        return
    row = val.get("after")
    if not row:
        return
    tx_id = row.get("transaction_id")
    if not tx_id:
        return
    raw_records.append({
        "transaction_id":    str(tx_id),
        "decision_label":    int(row.get("decision_label", 1)),
        "inspection_status": str(row.get("inspection_status", "PROCESSED")),
        "inspector_id":      str(row.get("inspector_id") or ""),
        "reason":            str(row.get("reason") or "Auditor decision"),
        "decided_at":        str(row.get("decided_at") or "")[:19],
    })

# --- Warm-up: join group + chờ rebalance ---
print("Warming up consumer (waiting for group rebalance)...")
warmup_dict = consumer.poll(timeout_ms=10000)
time.sleep(3)
assignment = consumer.assignment()
print(f"Assigned partitions: {assignment}")
if not assignment:
    print("[ERROR] No partition assigned after warm-up. Coordinator issue.")
    consumer.close()
    raise SystemExit(1)

# Process messages từ warm-up poll
for tp, messages in warmup_dict.items():
    for msg in messages:
        process_message(msg)
print(f"Warm-up processed {len(raw_records)} records so far")

# --- Main poll loop ---
empty_polls = 0
for _ in range(10):
    msg_dict = consumer.poll(timeout_ms=5000, max_records=5000)
    if not msg_dict:
        empty_polls += 1
        if empty_polls >= 2:
            break
        continue
    empty_polls = 0
    for tp, messages in msg_dict.items():
        for msg in messages:
            process_message(msg)

consumer.close()
print(f"Fetched {len(raw_records)} CDC events from Kafka topic '{FEEDBACK_TOPIC}'.")

if not raw_records:
    print("[INFO] No pending auditor feedback messages. Exiting.")
    raise SystemExit(0)

# 2. Deduplicate by transaction_id (keep latest decided_at)
dedup_dict = {}
for r in raw_records:
    tx = r["transaction_id"]
    prev = dedup_dict.get(tx)
    if prev is None or (r["decided_at"] or "") > (prev["decided_at"] or ""):
        dedup_dict[tx] = r
unique_records = list(dedup_dict.values())
print(f"Found {len(unique_records)} unique transaction verdicts to merge.")


# 3. Spark session
spark = (
    SparkSession.builder.appName("Delta_Feedback_Merge_Loop")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

feedback_df = spark.createDataFrame(unique_records)
print("\n[Preview Feedback Decisions to Merge]:")
feedback_df.show(5, truncate=False)


# 4. MERGE INTO Gold risk_scores (only update verdict columns)
if DeltaTable.isDeltaTable(spark, GOLD_RISK_SCORES):
    print(f"\n[STEP 1] MERGE INTO Gold: {GOLD_RISK_SCORES}...")
    DeltaTable.forPath(spark, GOLD_RISK_SCORES).alias("gold").merge(
        source=feedback_df.alias("fb"),
        condition="gold.transaction_id = fb.transaction_id"
    ).whenMatchedUpdate(set={
        "inspection_status": col("fb.inspection_status"),
    }).execute()
    print("Successfully executed Delta MERGE into Gold risk_scores!")
else:
    print(f"[WARN] Target Gold Delta table not found at {GOLD_RISK_SCORES}")


# 5. MERGE INTO Silver inspection_decisions (upsert full record)
if DeltaTable.isDeltaTable(spark, SILVER_DECISIONS):
    print(f"\n[STEP 2] MERGE INTO Silver: {SILVER_DECISIONS}...")
    DeltaTable.forPath(spark, SILVER_DECISIONS).alias("silver").merge(
        source=feedback_df.alias("fb"),
        condition="silver.transaction_id = fb.transaction_id"
    ).whenMatchedUpdate(set={
        "decision_label":    col("fb.decision_label"),
        "inspection_status": col("fb.inspection_status"),
        "inspector_id":      col("fb.inspector_id"),
        "reason":            col("fb.reason"),
        "decided_at":        col("fb.decided_at"),
    }).whenNotMatchedInsert(values={
        "transaction_id":    col("fb.transaction_id"),
        "decision_label":    col("fb.decision_label"),
        "inspection_status": col("fb.inspection_status"),
        "inspector_id":      col("fb.inspector_id"),
        "reason":            col("fb.reason"),
        "decided_at":        col("fb.decided_at"),
    }).execute()
    print("Successfully merged into Silver inspection_decisions!")
else:
    print(f"\n[STEP 2] Initializing Silver: {SILVER_DECISIONS}...")
    feedback_df.write.format("delta").mode("overwrite").save(SILVER_DECISIONS)
    print("Initialized Silver inspection_decisions Delta Table!")

spark.stop()
print("\nFeedback Loop closed: CockroachDB Changefeed -> Kafka -> Delta MERGE")