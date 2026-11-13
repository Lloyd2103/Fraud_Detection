"""
Delta Config service.

Everything returned here is measured at request time (Delta table metadata on HDFS, WebHDFS file
status, installed library versions, a Kafka socket check and a CockroachDB query). Anything that
cannot be measured is returned as null / "Unavailable ..." rather than a made-up value.
"""
import importlib.metadata
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from app.common.cache import TTLCache
from app.config.settings import settings
from app.database.session import SessionLocal
from app.integrations.delta_lake import get_delta_table, resolve_table_paths
from app.integrations.kafka import check_kafka_connectivity

CACHE_TTL_DELTA_CONFIG = 30.0
UNREACHABLE = "Unavailable (HDFS unreachable)"

# (tier label, table name used by get_delta_table / resolve_table_paths)
MEDALLION_TABLES: List[Tuple[str, str]] = [
    ("Silver", "silver/transactions"),
    ("Silver States", "silver/customer_states"),
    ("Silver Decisions", "silver/inspection_decisions"),
    ("Features", "features"),
    ("Gold", "gold/risk_scores"),
]

# Constraints required by the spec, checked against the live table metadata.
EXPECTED_CONSTRAINTS = [
    ("positive_amount", "Silver Transactions", "silver/transactions", "CRITICAL",
     "Transaction amount must be strictly positive."),
    ("valid_trans_type", "Silver Transactions", "silver/transactions", "HIGH",
     "Restricts transactions to the valid banking transaction types."),
    ("amount_positive", "Gold Risk Scores", "gold/risk_scores", "CRITICAL",
     "Amount must be positive before a risk score is recorded."),
    ("risk_score_range", "Gold Risk Scores", "gold/risk_scores", "CRITICAL",
     "Risk score must stay inside the probability interval [0.0, 1.0]."),
]


def _installed_version(package: str) -> Optional[str]:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def _spark_version() -> Optional[str]:
    version = _installed_version("pyspark")
    if version:
        return version
    release_file = os.path.join(settings.SPARK_HOME, "RELEASE") if settings.SPARK_HOME else ""
    if release_file and os.path.exists(release_file):
        with open(release_file, "r", encoding="utf-8") as fh:
            parts = fh.readline().split()
            if len(parts) >= 2 and parts[0] == "Spark":
                return parts[1]
    return None


def _hadoop_version() -> Optional[str]:
    if not settings.HADOOP_HOME:
        return None
    binary = os.path.join(settings.HADOOP_HOME, "bin", "hadoop")
    if not os.path.exists(binary):
        return None
    try:
        out = subprocess.run([binary, "version"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=8, text=True).stdout
        first = out.splitlines()[0].split() if out else []
        return first[1] if len(first) >= 2 and first[0] == "Hadoop" else None
    except (OSError, subprocess.SubprocessError):
        return None


def _hdfs_replication(table_name: str) -> Optional[int]:
    """Replication factor of the first file in the table's _delta_log, read from WebHDFS."""
    url = resolve_table_paths(table_name)["webhdfs_log"] + "?op=LISTSTATUS"
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            statuses = json.load(resp)["FileStatuses"]["FileStatus"]
        for st in statuses:
            if st.get("type") == "FILE":
                return int(st["replication"])
    except (OSError, ValueError, KeyError):
        pass
    return None


def _table_info(table_name: str) -> Dict[str, Any]:
    """Live info for one Delta table, or {'reachable': False}."""
    try:
        dt = get_delta_table(table_name)
        history = dt.history(limit=1)
        last_commit = history[0] if history else {}
        ts = last_commit.get("timestamp")
        return {
            "reachable": True,
            "version": dt.version(),
            "files": len(dt.file_uris()),
            "last_commit_at": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None,
            "last_operation": last_commit.get("operation"),
            "properties": dict(dt.metadata().configuration or {}),
        }
    except Exception as exc:  # delta-rs raises many error types for storage failures
        return {"reachable": False, "error": str(exc)[:120]}


class DeltaConfigService:
    def __init__(self):
        self._cache = TTLCache(default_ttl_seconds=CACHE_TTL_DELTA_CONFIG)

    def get_delta_configuration(self) -> Dict[str, Any]:
        cached = self._cache.get("config")
        if cached:
            return cached
        result = self._build()
        self._cache.set("config", result)
        return result

    # ------------------------------------------------------------------
    def _serving_db_info(self) -> Dict[str, Any]:
        try:
            with SessionLocal() as db:
                version = db.execute(text("SELECT version()")).scalar()
                total = db.execute(text("SELECT count(*) FROM transactions")).scalar()
            return {"status": "CONNECTED", "server_version": str(version)[:120], "total_serving_records": int(total or 0)}
        except Exception as exc:
            return {"status": f"ERROR: {str(exc)[:60]}", "server_version": None, "total_serving_records": None}

    def _build(self) -> Dict[str, Any]:
        infos = {name: _table_info(name) for _, name in MEDALLION_TABLES}
        gold = infos["gold/risk_scores"]
        silver = infos["silver/transactions"]
        any_reachable = any(i["reachable"] for i in infos.values())

        kafka_ok, kafka_host, kafka_port = check_kafka_connectivity(timeout=1.5)
        serving = self._serving_db_info()
        replication = _hdfs_replication("gold/risk_scores") if any_reachable else None
        delta_spark = _installed_version("delta-spark")
        delta_rs = _installed_version("deltalake")
        # delta-spark is the Delta Lake release; the python `deltalake` package is delta-rs, a different version line.
        delta_label = f"Delta Lake {delta_spark}" if delta_spark else (f"delta-rs (deltalake) {delta_rs}" if delta_rs else None)

        medallion_tables = []
        for tier, name in MEDALLION_TABLES:
            info = infos[name]
            row = {
                "tier": tier,
                "name": name,
                "path": resolve_table_paths(name)["hdfs_uri"],
                "format": "Delta Lake (Parquet + _delta_log)",
                "storage_target": "HDFS",
            }
            if info["reachable"]:
                row.update({
                    "status": f"AVAILABLE (v{info['version']})",
                    "frequency": f"{info['files']} data files; last commit {info['last_commit_at'] or 'n/a'} ({info['last_operation'] or 'n/a'})",
                    "role": "Delta table on HDFS",
                })
            else:
                row.update({"status": UNREACHABLE, "frequency": "—", "role": "Delta table on HDFS"})
            medallion_tables.append(row)
        medallion_tables.append({
            "tier": "Serving",
            "name": "system_db.transactions",
            "path": "CockroachDB / system_db",
            "format": "SQL table (PostgreSQL wire protocol)",
            "storage_target": "CockroachDB",
            "status": serving["status"],
            "frequency": "Gold-to-serving sync job (CDF)",
            "role": f"Serving store ({serving['total_serving_records']:,} rows)" if serving["total_serving_records"] is not None else "Serving store",
        })

        def prop(info: Dict[str, Any], key: str) -> str:
            if not info["reachable"]:
                return UNREACHABLE
            return info["properties"].get(key, "Not set")

        table_properties = [
            {"property": "delta.enableChangeDataFeed", "value": prop(gold, "delta.enableChangeDataFeed"),
             "scope": "Gold Risk Scores (HDFS)",
             "description": "Change Data Feed: row-level change log read by the serving sync job."},
            {"property": "delta.deletedFileRetentionDuration", "value": prop(silver, "delta.deletedFileRetentionDuration"),
             "scope": "Silver Transactions (HDFS)",
             "description": "How long removed data files are kept for Time Travel before VACUUM."},
            {"property": "delta.logRetentionDuration", "value": prop(silver, "delta.logRetentionDuration"),
             "scope": "Silver Transactions (HDFS)",
             "description": "How long commit history is kept in _delta_log."},
            {"property": "delta.autoOptimize.optimizeWrite", "value": prop(silver, "delta.autoOptimize.optimizeWrite"),
             "scope": "Silver Transactions (HDFS)",
             "description": "Bin-packs small files at write time."},
        ]
        for p in table_properties:
            p["status"] = "Unavailable" if p["value"] == UNREACHABLE else ("Not set" if p["value"] == "Not set" else "SET")

        check_constraints = []
        for name, label, table_name, severity, description in EXPECTED_CONSTRAINTS:
            info = infos[table_name]
            key = f"delta.constraints.{name}"
            prop_val = info["properties"].get(key)
            if prop_val is None and name == "positive_amount":
                prop_val = info["properties"].get("delta.constraints.so_tien_duong")

            if not info["reachable"]:
                expression, status = "—", UNREACHABLE
            elif prop_val is not None:
                expression, status = prop_val, "ENFORCED"
            else:
                expression, status = "—", "Not set"
            check_constraints.append({
                "name": name, "table": label, "expression": expression, "status": status,
                "severity": severity, "description": description, "note": None,
            })

        return {
            "status": "success",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "infrastructure": {
                "spark_version": _spark_version(),
                "delta_lake_version": delta_label,
                "hadoop_version": _hadoop_version(),
                "hdfs_namenode": settings.HDFS_URL,
                "replication_factor": replication,
                "hdfs": {
                    "host": settings.HDFS_HOST,
                    "port": settings.HDFS_PORT,
                    "namenode_uri": settings.HDFS_URL,
                    "hadoop_version": _hadoop_version(),
                    "replication": replication,
                    "status": "CONNECTED" if any_reachable else UNREACHABLE,
                    "root_path": "/lakehouse/fraud_detection",
                },
                "gold_serving_db": {
                    "engine": serving["server_version"],
                    "serving_database": "system_db",
                    "primary_table": "transactions",
                    "status": serving["status"],
                    "total_serving_records": serving["total_serving_records"],
                },
                "kafka": {
                    "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                    "ingestion_topic": settings.KAFKA_TOPIC_TRANSACTIONS,
                    "alerts_topic": settings.KAFKA_TOPIC_ALERTS,
                    "status": "REACHABLE" if kafka_ok else f"UNREACHABLE ({kafka_host}:{kafka_port})",
                },
                "compute_engine": {
                    "spark": _spark_version(),
                    "delta": delta_label,
                },
            },
            "medallion_tables": medallion_tables,
            "table_properties": table_properties,
            "check_constraints": check_constraints,
        }


delta_config_service = DeltaConfigService()
