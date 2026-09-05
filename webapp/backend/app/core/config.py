"""
Core Configuration Module for Real-time Fraud Detection WebApp
Synchronized with HDFS Lakehouse, Spark Jobs, Airflow DAGs, and Kafka Topics.
DO NOT CHANGE paths here without checking spark_jobs/ and conf/.
"""

import os
from pydantic import BaseModel

class Settings(BaseModel):
    # App Information
    APP_NAME: str = "Real-Time Credit Card Fraud Detection Platform"
    APP_CODE: str = "bd02_gian_lan"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")
    
    # HDFS & Namenode Configuration
    # Matches core-site.xml: fs.defaultFS = hdfs://labsoe-17:9000
    NAMENODE_HOST: str = os.getenv("NAMENODE_HOST", "labsoe-17")
    NAMENODE_PORT: int = int(os.getenv("NAMENODE_PORT", "9000"))
    HDFS_URL: str = f"hdfs://{NAMENODE_HOST}:{NAMENODE_PORT}"
    
    # Delta Lakehouse Base Path - Exactly matches spark_jobs paths
    LAKEHOUSE_BASE: str = f"{HDFS_URL}/lakehouse/fraud_detection"
    
    # Medallion Architecture Table Paths (Delta Lake)
    BRONZE_TX_PATH: str = f"{LAKEHOUSE_BASE}/bronze"
    SILVER_TX_PATH: str = f"{LAKEHOUSE_BASE}/silver/transactions"
    SILVER_STATES_PATH: str = f"{LAKEHOUSE_BASE}/silver/customer_states"
    SILVER_DECISIONS_PATH: str = f"{LAKEHOUSE_BASE}/silver/inspection_decisions"
    FEATURES_PATH: str = f"{LAKEHOUSE_BASE}/features"
    QUARANTINE_PATH: str = f"{LAKEHOUSE_BASE}/_quarantine"
    
    # Gold Analytics & Serving Tables
    GOLD_RISK_SCORES_PATH: str = f"{LAKEHOUSE_BASE}/gold/risk_scores"
    GOLD_FRAUD_SUMMARY_PATH: str = f"{LAKEHOUSE_BASE}/gold/fraud_summary"
    GOLD_MODEL_PERF_PATH: str = f"{LAKEHOUSE_BASE}/gold/model_performance_comparison"
    GOLD_DRIFT_PATH: str = f"{LAKEHOUSE_BASE}/gold/drift_monitoring"
    
    # ML Models Paths on HDFS
    MODEL_GBT_PATH: str = f"{LAKEHOUSE_BASE}/models/gbt_fraud_model"
    MODEL_RF_PATH: str = f"{LAKEHOUSE_BASE}/models/random_forest_fraud_model"
    
    # Kafka Streaming Configuration
    # Matches kafka_producer.py and bronze_ingestion.py
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.200:9092")
    KAFKA_TOPIC_TRANSACTIONS: str = "transactions"
    KAFKA_TOPIC_ALERTS: str = "fraud_alerts"
    
    # Thresholds & SLA (per DeTai_2.pdf requirements)
    RISK_THRESHOLD_HIGH: float = 0.80
    RISK_THRESHOLD_MEDIUM: float = 0.50
    DAILY_ALERT_CAPACITY: int = 200  # Precision@200/day
    SLA_LATENCY_MAX_SECONDS: float = 5.0  # Alert display SLA < 5s
    
    # WebApp Server Host & Port
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

settings = Settings()
