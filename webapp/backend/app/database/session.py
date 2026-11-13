import os
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql.base import PGDialect
from dotenv import load_dotenv

# Patch PGDialect to support CockroachDB version string
def _safe_server_version_info(self, connection):
    try:
        v = connection.exec_driver_sql("select version()").scalar()
        m = re.match(r".*(?:PostgreSQL|EnterpriseDB) +(\d+)\.(\d+)(?:\.(\d+))?", str(v))
        if m:
            return tuple(int(x) for x in m.groups() if x is not None)
    except Exception:
        pass
    return (14, 0, 0)

PGDialect._get_server_version_info = _safe_server_version_info

for p in [
    Path(__file__).resolve().parents[4] / ".env",
    Path(__file__).resolve().parents[3] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
    Path(".env"),
]:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Define it in the .env file before starting the backend.")
if DATABASE_URL.startswith("cockroachdb"):
    DATABASE_URL = re.sub(r"^cockroachdb(?:\+[^:]+)?://", "postgresql+psycopg2://", DATABASE_URL)
    if "sslmode=" not in DATABASE_URL:
        DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "sslmode=disable"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
).execution_options(stream_results=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy_cockroachdb import run_transaction

def run_db_transaction(callback, max_retries: int = 5, max_backoff: int = 2):
    """
    Executes a write transaction with CockroachDB Automatic Client-Side Retry.
    Handles SQLState 40001 (TransactionRetryWithProtoRefreshError) at SERIALIZABLE isolation level.
    Retries up to max_retries times with exponential backoff.
    """
    return run_transaction(SessionLocal, callback, max_retries=max_retries, max_backoff=max_backoff)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

