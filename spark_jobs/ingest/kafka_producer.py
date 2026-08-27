import csv
import json
import time
import random
from datetime import datetime, timedelta
from kafka import KafkaProducer

# Configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC_NAME = "transactions"
CSV_FILE_PATH = "/home/master/PS_20174392719_1491204439457_log.csv"

# Mapping transaction types to system channels
CHANNELS = ["ATM", "POS", "ONLINE", "APP"]

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def stream_transactions():
    print("Starting Kafka Producer...")
    base_time = datetime.now()

    with open(CSV_FILE_PATH, mode="r") as file:
        reader = csv.DictReader(file)
        current_step = 1
        step_records = []

        for row in reader:
            step = int(row["step"])

            # PaySim schema: step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud
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
                # Flush previous step with simulated out-of-order latency
                flush_step_records(step_records, base_time, current_step)
                current_step = step
                step_records = [record]
                time.sleep(10)  # Each simulation step compresses into 10 real seconds

def flush_step_records(records, base_time, step):
    now = datetime.now()
    for record in records:
        # Simulate out-of-order transaction timestamp up to 30 seconds
        delay_seconds = random.randint(0, 30)
        event_time = now - timedelta(seconds=delay_seconds)
        
        record["timestamp"] = event_time.strftime("%Y-%m-%d %H:%M:%S")
        record["received_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        record["partition_date"] = event_time.strftime("%Y-%m-%d")

        producer.send(TOPIC_NAME, value=record)
    
    producer.flush()
    print(f"Pushed {len(records)} transactions for Step {step}")

if __name__ == "__main__":
    stream_transactions()
