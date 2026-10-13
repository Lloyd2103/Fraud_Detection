import os
import json
from dotenv import load_dotenv
from kafka import KafkaConsumer, TopicPartition

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

bootstrap_servers = [s.strip() for s in os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.200:9092,127.0.0.1:9092").split(",")]
alerts_topic = os.getenv("KAFKA_ALERTS_TOPIC", "alerts")

c = KafkaConsumer(bootstrap_servers=bootstrap_servers,
                  api_version=(2,5,0), enable_auto_commit=False,
                  consumer_timeout_ms=5000)
tp = TopicPartition(alerts_topic, 0)

c.assign([tp])
c.seek(tp, 0)

for tp, msgs in c.poll(timeout_ms=3000).items():
    for msg in msgs[:3]:
        a = json.loads(msg.value.decode())
        print(json.dumps(a, indent=2, ensure_ascii=False))
        print('---')
        break
c.close()