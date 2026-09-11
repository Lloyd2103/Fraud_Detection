"""
Core Configuration Module for Real-time Fraud Detection WebApp
Synchronized with HDFS Lakehouse, Spark Jobs, Airflow DAGs, Kafka Topics, and DeTai2.pdf.
"""

import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Locate and load .env file from project root
env_paths = [
    Path(__file__).resolve().parents[4] / ".env",  # /home/master/fraud_detection/.env
    Path(__file__).resolve().parents[3] / ".env",
    Path(".env"),
]
for p in env_paths:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break

class Settings(BaseModel):
    # App Information
    APP_NAME: str = "Real-Time Credit Card Fraud Detection Platform"
    APP_CODE: str = "Fraud Detection"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")
    
    # Master Node & Network
    MASTER_IP: str = os.getenv("MASTER_IP", "192.168.80.200")
    
    # HDFS & Namenode Configuration
    # Synchronized with .env (HDFS_HOST / HDFS_PORT) and core-site.xml (fs.defaultFS = hdfs://labsoe-17:9000)
    HDFS_HOST: str = os.getenv("HDFS_HOST", os.getenv("NAMENODE_HOST", "labsoe-17"))
    HDFS_PORT: int = int(os.getenv("HDFS_PORT", os.getenv("NAMENODE_PORT", "9000")))
    NAMENODE_HOST: str = HDFS_HOST
    NAMENODE_PORT: int = HDFS_PORT
    HDFS_URL: str = f"hdfs://{HDFS_HOST}:{HDFS_PORT}"
    
    # Delta Lakehouse Base Path - Exactly matches spark_jobs paths
    LAKEHOUSE_BASE: str = f"{HDFS_URL}/lakehouse/fraud_detection"
    
    # Medallion Architecture Table Paths (Delta Lake) - Both English and Vietnamese DeTai2.pdf specs
    BRONZE_TX_PATH: str = f"{LAKEHOUSE_BASE}/bronze"
    BRONZE_TX_SUBPATH: str = f"{LAKEHOUSE_BASE}/bronze/transactions"
    BRONZE_GIAO_DICH_PATH: str = f"{LAKEHOUSE_BASE}/bronze/transactions"
    
    SILVER_TX_PATH: str = f"{LAKEHOUSE_BASE}/silver/transactions"
    SILVER_GIAO_DICH_PATH: str = f"{LAKEHOUSE_BASE}/silver/transactions"
    
    SILVER_STATES_PATH: str = f"{LAKEHOUSE_BASE}/silver/customer_states"
    SILVER_TRANG_THAI_KHACH_HANG_PATH: str = f"{LAKEHOUSE_BASE}/silver/customer_states"
    
    SILVER_DECISIONS_PATH: str = f"{LAKEHOUSE_BASE}/silver/inspection_decisions"
    SILVER_KET_LUAN_THAM_DINH_PATH: str = f"{LAKEHOUSE_BASE}/silver/ket_luan_tham_dinh"
    
    FEATURES_PATH: str = f"{LAKEHOUSE_BASE}/features"
    QUARANTINE_PATH: str = f"{LAKEHOUSE_BASE}/_quarantine"
    
    # Gold Analytics & Serving Tables (DeTai2.pdf Section 2.4 & Section 2.7)
    GOLD_RISK_SCORES_PATH: str = f"{LAKEHOUSE_BASE}/gold/risk_scores"
    GOLD_DIEM_RUI_RO_PATH: str = f"{LAKEHOUSE_BASE}/gold/diem_rui_ro"
    
    GOLD_FRAUD_SUMMARY_PATH: str = f"{LAKEHOUSE_BASE}/gold/fraud_summary"
    GOLD_MODEL_PERF_PATH: str = f"{LAKEHOUSE_BASE}/gold/model_performance_comparison"
    GOLD_HIEU_NANG_MO_HINH_PATH: str = f"{LAKEHOUSE_BASE}/gold/model_performance_comparison"
    
    GOLD_DRIFT_PATH: str = f"{LAKEHOUSE_BASE}/gold/drift_monitoring"
    GOLD_THEO_DOI_DRIFT_PATH: str = f"{LAKEHOUSE_BASE}/gold/theo_doi_drift"
    
    # ML Models Paths on HDFS
    MODEL_GBT_PATH: str = f"{LAKEHOUSE_BASE}/models/gbt_fraud_model"
    MODEL_RF_PATH: str = f"{LAKEHOUSE_BASE}/models/random_forest_fraud_model"
    
    # Kafka Streaming Configuration
    # Synchronized with spark_jobs/streaming/fraud_detector.py (topic: alerts) and kafka_producer.py
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{MASTER_IP}:9092")
    KAFKA_TOPIC_TRANSACTIONS: str = os.getenv("KAFKA_TOPIC", "transactions")
    KAFKA_TOPIC_ALERTS: str = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")  # Fixed from fraud_alerts to alerts
    
    # Thresholds & SLA (per DeTai_2.pdf requirements)
    RISK_THRESHOLD_HIGH: float = 0.80
    RISK_THRESHOLD_MEDIUM: float = 0.50
    DAILY_ALERT_CAPACITY: int = 200  # Precision@200/day
    SLA_LATENCY_MAX_SECONDS: float = 5.0  # Alert display SLA < 5s
    
    # WebApp Server Host & Port
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

settings = Settings()
