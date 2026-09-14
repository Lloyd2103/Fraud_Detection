import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
for p in [Path(__file__).resolve().parents[4] / ".env", Path("/home/master/fraud_detection/.env")]:
    if p.exists():
        load_dotenv(p)
        break

class Settings:
    PROJECT_NAME: str = "Realtime Fraud Detection Review API"
    API_V1_STR: str = "/api"
    
    HDFS_HOST: str = os.getenv("HDFS_HOST", "labsoe-17")
    HDFS_PORT: int = int(os.getenv("HDFS_PORT", "9000"))
    HDFS_BASE_URL: str = os.getenv("HDFS_BASE_URL", f"hdfs://{HDFS_HOST}:{HDFS_PORT}")
    
    GOLD_RISK_SCORES_PATH: str = f"{HDFS_BASE_URL}/lakehouse/fraud_detection/gold/risk_scores"
    SILVER_VERDICTS_PATH: str = f"{HDFS_BASE_URL}/lakehouse/fraud_detection/silver/inspection_decisions"
    BRONZE_TRANSACTIONS_PATH: str = f"{HDFS_BASE_URL}/lakehouse/fraud_detection/bronze/transactions"

settings = Settings()