# System configurations for storage paths and server settings
import os

class Settings:
    PROJECT_NAME: str = "Realtime Fraud Detection Review API"
    API_V1_STR: str = "/api"
    
    # Explicit HDFS Namenode URL
    HDFS_BASE_URL: str = os.getenv("HDFS_BASE_URL", "hdfs://192.168.80.200:9000")
    GOLD_RISK_SCORES_PATH: str = f"{HDFS_BASE_URL}/lakehouse/fraud_detection/gold/risk_scores"
    SILVER_VERDICTS_PATH: str = f"{HDFS_BASE_URL}/lakehouse/fraud_detection/silver/inspection_decisions"
    BRONZE_TRANSACTIONS_PATH: str = f"{HDFS_BASE_URL}/lakehouse/fraud_detection/bronze/transactions"

settings = Settings()