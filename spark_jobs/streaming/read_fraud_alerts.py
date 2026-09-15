# Script doc tin nhan canh bao gian lan truc tiep tu partition topic 'alerts'
import json
import os
import sys
import time

def main():
    try:
        from kafka import KafkaConsumer, TopicPartition
    except ImportError:
        sys.exit(1)

    bootstrap_servers = ["192.168.80.200:9092"]
    topic_name = "alerts"

    print("REAL-TIME FRAUD ALERTS MONITORING CONSOLE")
    print(f"Target Broker : {bootstrap_servers}")
    print(f"Target Topic  : {topic_name}")
    print("Mode          : Direct Partition Assignment (No Group Coordinator)")

    sys.stdout.flush()

    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=False,
            consumer_timeout_ms=1000
        )

        tp = TopicPartition(topic_name, 0)
        consumer.assign([tp])

        end_offset = consumer.end_offsets([tp])[tp]
        start_offset = max(0, end_offset - 15)
        consumer.seek(tp, start_offset)

        print(f"[INFO] Total alerts in topic: {end_offset}")
        print(f"[INFO] Streaming alerts from offset {start_offset}...\n", flush=True)

        while True:
            records = consumer.poll(timeout_ms=500)
            if records:
                for tp_key, messages in records.items():
                    for msg in messages:
                        try:
                            alert = json.loads(msg.value.decode("utf-8"))
                        except Exception:
                            alert = {"raw_payload": msg.value.decode("utf-8", errors="ignore")}

                        tx_id = alert.get("transaction_id", "UNKNOWN")
                        src = alert.get("source_account", "UNKNOWN")
                        dst = alert.get("dest_account", "UNKNOWN")
                        amt = float(alert.get("amount", 0.0))
                        channel = alert.get("channel", "UNKNOWN")
                        pred = alert.get("fraud_prediction", 1.0)
                        ts = alert.get("alert_generated_at", "UNKNOWN")

                        print(
                            f"[FRAUD ALERT] Offset: {msg.offset:<5} | "
                            f"TX: {tx_id:<12} | "
                            f"{src} -> {dst} | "
                            f"Amount: {amt:>12,.2f} VND | "
                            f"Pred: {pred} | "
                            f"Channel: {channel:<6} | "
                            f"Time: {ts}",
                            flush=True
                        )
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[INFO] Alert monitoring terminated by user.")
    except Exception as exc:
        print(f"[ERROR] Consumer error: {exc}", file=sys.stderr)
    finally:
        try:
            consumer.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()