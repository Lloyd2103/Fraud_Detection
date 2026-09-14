import csv
import json
import time
import random
from datetime import datetime, timedelta
from kafka import KafkaProducer

import os

# Configuration (Centralized Environment Variables)
MASTER_IP = os.getenv("MASTER_IP", "192.168.80.200")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{MASTER_IP}:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "transactions")
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", "/home/master/PS_20174392719_1491204439457_log.csv")

CHANNELS = ["ATM", "POS", "ONLINE", "APP"]
BATCH_SIZE = 100  # Number of records per batch before flush

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    key_serializer=lambda k: k.encode('utf-8') if k else None,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def flush_step_records(records, step):
    now = datetime.now()
    processed_records = []

    # Step 1: Assign timestamps with random watermark delay (0-30s)
    for record in records:
        delay_seconds = random.randint(0, 30)
        event_time = now - timedelta(seconds=delay_seconds)
        record["timestamp"] = event_time.strftime("%Y-%m-%d %H:%M:%S")
        record["received_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        record["partition_date"] = event_time.strftime("%Y-%m-%d")
        processed_records.append(record)

    # Step 2: Shuffle records to simulate out-of-order data ingestion
    random.shuffle(processed_records)

    # Step 3: Publish records using key-based hashing (source_account) to guarantee account transaction ordering
    count = 0
    for record in processed_records:
        key = record["source_account"]
        producer.send(TOPIC_NAME, key=key, value=record)
        count += 1
        if count % BATCH_SIZE == 0:
            producer.flush()
            time.sleep(0.05)  # Throttle to prevent broker overload

    producer.flush()  # Flush remaining batch
    print(f"Pushed {len(processed_records)} out-of-order transactions via key-partitioning (Step {step})")


def stream_transactions():
    print("Starting Advanced Kafka Producer (Watermark Simulation Mode)...")

    with open(CSV_FILE_PATH, mode="r") as file:
        reader = csv.DictReader(file)
        current_step = 1
        step_records = []

        for row in reader:
            step = int(row["step"])
            record = {
                "transaction_id": f"TX_{step}_{random.randint(100000, 999999)}",
                "source_account": row["nameOrig"],
                "dest_account": row["nameDest"],
                "trans_type": row["type"],
                "amount": float(row["amount"]),
                "old_balance_source": float(row["oldbalanceOrg"]),
                "new_balance_source": float(row["newbalanceOrig"]),
                "old_balance_dest": float(row["oldbalanceDest"]),
                "new_balance_dest": float(row["newbalanceDest"]),
                "channel": random.choice(CHANNELS),
                "is_fraud_label": int(row["isFraud"])
            }

            if step == current_step:
                step_records.append(record)
            else:
                flush_step_records(step_records, current_step)
                current_step = step
                step_records = [record]
                time.sleep(10)  # Compress 1 simulation hour into 10 seconds real-time


        # Process final step
        if step_records:
            flush_step_records(step_records, current_step)



if __name__ == "__main__":
    stream_transactions()