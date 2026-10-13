import csv
import json
import os
import random
import time
from datetime import datetime, timedelta
from kafka import KafkaProducer


# Configuration
MASTER_IP = os.getenv("MASTER_IP", "192.168.80.200")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{MASTER_IP}:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "transactions")
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", "/home/fraud/synthetic_transactions.csv")

START_STEP = int(os.getenv("START_STEP", "1"))
MAX_STEP   = int(os.getenv("MAX_STEP", "0"))          # 0 = no limit
STEP_DELAY = float(os.getenv("STEP_DELAY", "0"))       # seconds between steps
SHUFFLE_BUFFER_SIZE = int(os.getenv("SHUFFLE_BUFFER_SIZE", "0"))
RECEIVED_AT_JITTER_MAX = int(os.getenv("RECEIVED_AT_JITTER_MAX", "0"))
LOG_EVERY_SECONDS = float(os.getenv("LOG_EVERY_SECONDS", "5"))
FLUSH_EVERY_N = int(os.getenv("FLUSH_EVERY_N", "1000"))

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    key_serializer=lambda k: k.encode("utf-8") if k else None,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    acks=1,
    linger_ms=10,
    batch_size=65536,
    max_in_flight_requests_per_connection=5,
)

def on_send_error(exc):
    print(f"[ERROR] Failed to send: {exc}", flush=True)

# Payload mapping
def csv_row_to_payload(row: dict) -> dict:
    ts = row["timestamp"]

    use_wallclock = os.getenv("USE_WALLCLOCK_RECEIVED_AT", "true").lower() == "true"
    if use_wallclock:
        received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif RECEIVED_AT_JITTER_MAX > 0:
        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        jitter = random.randint(1, RECEIVED_AT_JITTER_MAX)
        received_at = (ts_dt + timedelta(seconds=jitter)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        received_at = ts

    return {
        "transaction_id":     row["transaction_id"],
        "source_account":     row["nameOrig"],
        "dest_account":       row["nameDest"],
        "trans_type":         row["type"],
        "amount":             float(row["amount"]),
        "old_balance_source": float(row["oldbalanceOrg"]),
        "new_balance_source": float(row["newbalanceOrig"]),
        "old_balance_dest":   float(row["oldbalanceDest"]),
        "new_balance_dest":   float(row["newbalanceDest"]),
        "channel":            row["channel"],
        "timestamp":          ts,
        "received_at":        received_at,
        "partition_date":     ts[:10],
    }


def stream_by_step():
    start_time = time.time()
    total_sent = 0
    total_steps = 0
    last_log_time = start_time

    print("=" * 60)
    print("  KAFKA PRODUCER (STEP-BASED)")
    print("=" * 60)
    print(f"  CSV:            {CSV_FILE_PATH}")
    print(f"  Kafka:          {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  Topic:          {TOPIC_NAME}")
    print(f"  Step range:     [{START_STEP} .. {MAX_STEP if MAX_STEP > 0 else 'END'}]")
    print(f"  Step delay:     {STEP_DELAY}s" if STEP_DELAY > 0 else "  Step delay:     NONE (backfill)")
    print(f"  Shuffle:        {SHUFFLE_BUFFER_SIZE}" if SHUFFLE_BUFFER_SIZE > 0 else "  Shuffle:        OFF")
    print(f"  Jitter:         {RECEIVED_AT_JITTER_MAX}s" if RECEIVED_AT_JITTER_MAX > 0 else "  Jitter:         NONE")
    print("=" * 60)

    if not os.path.exists(CSV_FILE_PATH):
        print(f"[ERROR] CSV not found: {CSV_FILE_PATH}")
        return

    try:
        with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            required = {
                "step", "transaction_id", "timestamp", "type", "amount",
                "nameOrig", "oldbalanceOrg", "newbalanceOrig",
                "nameDest", "oldbalanceDest", "newbalanceDest", "channel",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                print(f"[ERROR] CSV missing columns: {sorted(missing)}")
                return

            current_step = None
            step_buffer = []

            def flush_step(step_id: int, rows: list):
                """Send all rows of one step, with optional shuffle."""
                nonlocal total_sent, last_log_time

                if SHUFFLE_BUFFER_SIZE > 0 and len(rows) > 1:
                    random.shuffle(rows)

                for r in rows:
                    producer.send(
                        TOPIC_NAME,
                        key=r["nameOrig"],
                        value=csv_row_to_payload(r),
                    ).add_errback(on_send_error)
                    total_sent += 1

                producer.flush()

                now = time.time()
                if now - last_log_time >= LOG_EVERY_SECONDS:
                    elapsed = now - start_time
                    rate = total_sent / elapsed if elapsed > 0 else 0
                    print(
                        f"[STEP {step_id:>4}] Sent: {total_sent:>10,} | "
                        f"Rate: {rate:>7,.0f} tx/s | "
                        f"Elapsed: {elapsed:>6.1f}s",
                        flush=True,
                    )
                    last_log_time = now

            for row in reader:
                step = int(row["step"])

                # Skip steps before START_STEP
                if step < START_STEP:
                    continue

                # Stop at MAX_STEP
                if MAX_STEP > 0 and step > MAX_STEP:
                    break

                if step != current_step:
                    if step_buffer:
                        flush_step(current_step, step_buffer)
                        total_steps += 1
                        step_buffer = []
                        if STEP_DELAY > 0:
                            time.sleep(STEP_DELAY)
                    current_step = step

                step_buffer.append(row)

            # Final flush
            if step_buffer:
                flush_step(current_step, step_buffer)
                total_steps += 1

            producer.flush()

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")

    finally:
        producer.flush()
        producer.close()
        elapsed = time.time() - start_time
        rate = total_sent / elapsed if elapsed > 0 else 0
        print("\n" + "=" * 60)
        print("  PRODUCER COMPLETE")
        print("=" * 60)
        print(f"  Total sent:    {total_sent:,} transactions")
        print(f"  Total steps:   {total_steps:,}")
        print(f"  Elapsed:       {elapsed:.2f} seconds")
        print(f"  Avg rate:      {rate:,.0f} tx/s")
        print("=" * 60)


if __name__ == "__main__":
    stream_by_step()