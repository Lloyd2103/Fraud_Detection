"""
Application settings: the single source of truth for configuration.

All deployment-specific values (hosts, ports, credentials, secrets) come from
environment variables / the project's .env file. Secrets have NO defaults.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Locate and load the .env file (project root first, then closer parents, then CWD).
_here = Path(__file__).resolve()
for _p in (
    _here.parents[4] / ".env",
    _here.parents[3] / ".env",
    _here.parents[2] / ".env",
    Path(".env"),
):
    if _p.exists():
        load_dotenv(dotenv_path=_p)
        break


_HDFS_HOST = os.getenv("HDFS_HOST", os.getenv("NAMENODE_HOST", "labsoe-17"))
_HDFS_PORT = int(os.getenv("HDFS_PORT", os.getenv("NAMENODE_PORT", "9000")))
_HDFS_URL = f"hdfs://{_HDFS_HOST}:{_HDFS_PORT}"
_MASTER_IP = os.getenv("MASTER_IP", "")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("true", "1", "yes")


class Settings(BaseModel):
    # ---- App ----
    APP_NAME: str = "Real-Time Credit Card Fraud Detection Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = _env_bool("DEBUG", False)

    # ---- Network ----
    MASTER_IP: str = _MASTER_IP

    # ---- HDFS / Lakehouse ----
    HDFS_HOST: str = _HDFS_HOST
    HDFS_PORT: int = _HDFS_PORT
    NAMENODE_HOST: str = _HDFS_HOST
    NAMENODE_PORT: int = _HDFS_PORT
    HDFS_URL: str = _HDFS_URL
    LAKEHOUSE_BASE: str = f"{_HDFS_URL}/lakehouse/fraud_detection"
    GOLD_RISK_SCORES_PATH: str = f"{_HDFS_URL}/lakehouse/fraud_detection/gold/risk_scores"

    # ---- Kafka ----
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", f"{_MASTER_IP or 'localhost'}:9092"
    )
    KAFKA_TOPIC_TRANSACTIONS: str = os.getenv("KAFKA_TOPIC", "transactions")
    KAFKA_TOPIC_ALERTS: str = os.getenv("KAFKA_TOPIC_ALERTS") or os.getenv("KAFKA_ALERTS_TOPIC", "alerts")

    # ---- Risk thresholds and SLA (spec sections 2.1 and 2.8) ----
    RISK_THRESHOLD_HIGH: float = 0.80
    RISK_THRESHOLD_MEDIUM: float = 0.50
    DAILY_ALERT_CAPACITY: int = 200
    SLA_SCORING_SECONDS: float = 2.0     # scoring latency target (spec 2.1)
    SLA_LATENCY_MAX_SECONDS: float = 5.0  # alert-on-web target (spec 2.8)

    # ---- Web server ----
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "")  # comma-separated; empty = same-origin only
    USE_SECURE_COOKIE: bool = _env_bool("USE_SECURE_COOKIE", True)

    # ---- Serving database (CockroachDB, PostgreSQL wire protocol) ----
    # No default: a missing DATABASE_URL must fail loudly instead of connecting to a made-up host.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ---- Pipeline-to-web shared secret (header X-Pipeline-Secret). No default. ----
    # The training job (spark_jobs/ml/train_model.py) sends INTERNAL_SECRET_KEY, so accept it as the fallback name.
    PIPELINE_INTERNAL_SECRET: str = os.getenv("PIPELINE_INTERNAL_SECRET") or os.getenv("INTERNAL_SECRET_KEY", "")

    # ---- Local installation paths (only used by the optional Spark session / version probe) ----
    HADOOP_HOME: str = os.getenv("HADOOP_HOME", "")
    SPARK_HOME: str = os.getenv("SPARK_HOME", "")
    EVAL_RESULTS_DIR: str = os.getenv("EVAL_RESULTS_DIR", "")


settings = Settings()
