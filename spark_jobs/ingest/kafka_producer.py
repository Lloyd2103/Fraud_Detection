import csv
import json
import time
import random
from datetime import datetime, timedelta
from kafka import KafkaProducer

# Configuration
# Đổi sang IP thật để máy Worker có thể giao tiếp kéo luồng dữ liệu phân tán
KAFKA_BOOTSTRAP_SERVERS = "192.168.80.200:9092"
TOPIC_NAME = "transactions"
CSV_FILE_PATH = "/home/master/PS_20174392719_1491204439457_log.csv"

# Mapping transaction types to system channels
CHANNELS = ["ATM", "POS", "ONLINE", "APP"]

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

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
                # Thực hiện xả dữ liệu step cũ
                flush_step_records(step_records, current_step)
                current_step = step
                step_records = [record]
                time.sleep(10)  # Nén 1 giờ mô phỏng thành 10 giây thực tế

        # Đảm bảo xả nốt step cuối cùng khi kết thúc file
        if step_records:
            flush_step_records(step_records, current_step)

def flush_step_records(records, step):
    now = datetime.now()
    processed_records = []

    # BƯỚC 1: Tạo độ trễ và nhãn thời gian cho từng bản ghi độc lập
    for record in records:
        # Mô phỏng giao dịch bị trễ mạng/lệch thứ tự lên tới 30 giây theo yêu cầu bắt buộc
        delay_seconds = random.randint(0, 30)
        event_time = now - timedelta(seconds=delay_seconds)
        
        record["timestamp"] = event_time.strftime("%Y-%m-%d %H:%M:%S")
        record["received_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        record["partition_date"] = event_time.strftime("%Y-%m-%d")
        processed_records.append(record)
    
    # BƯỚC 2: RÀNG BUỘC PHẢI CÓ - Xáo trộn ngẫu nhiên vị trí các bản ghi (Physical Shuffle)
    # Việc này ép các tin nhắn có Event Time muộn bị ghi xen kẽ vào Kafka Partition
    random.shuffle(processed_records)

    # BƯỚC 3: Bắn dữ liệu lộn xộn vào Kafka Broker
    for record in processed_records:
        producer.send(TOPIC_NAME, value=record)
    
    producer.flush()
    print(f"Pushed {len(processed_records)} out-of-order transactions for Step {step}")

if __name__ == "__main__":
    stream_transactions()
