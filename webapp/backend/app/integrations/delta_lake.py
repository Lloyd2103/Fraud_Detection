"""
Delta Lake Integration Module
Provides path resolution and DeltaTable access over HDFS via deltalake (delta-rs).
Rule BE4 compliant: does NOT import any modules/.
"""
import os
from typing import Dict, Optional, Any
from deltalake import DeltaTable
from app.config.settings import settings

TABLE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "features": {
        "hdfs_path": f"{settings.LAKEHOUSE_BASE}/features",
        "id_col": "transaction_id",
        "val_col": "amt_norm",
    },
    "silver/transactions": {
        "hdfs_path": f"{settings.LAKEHOUSE_BASE}/silver/transactions",
        "id_col": "transaction_id",
        "val_col": "amount",
    },
    "silver/customer_states": {
        "hdfs_path": f"{settings.LAKEHOUSE_BASE}/silver/customer_states",
        "id_col": "account_id",
        "val_col": "last_known_balance",
    },
    "silver/inspection_decisions": {
        "hdfs_path": f"{settings.LAKEHOUSE_BASE}/silver/inspection_decisions",
        "id_col": "transaction_id",
        "val_col": "decision_label",
    },
    "gold/risk_scores": {
        "hdfs_path": f"{settings.LAKEHOUSE_BASE}/gold/risk_scores",
        "id_col": "transaction_id",
        "val_col": "risk_score",
    },
}

SUPPORTED_TABLES = list(TABLE_CONFIGS.keys())

def resolve_table_paths(table_name: str = "gold/risk_scores") -> Dict[str, str]:
    """Resolve a (possibly dotted/loosely typed) table name to its canonical name and HDFS/WebHDFS paths."""
    clean_table = (table_name or "gold/risk_scores").strip().lower().replace(".", "/")
    canonical_name = "gold/risk_scores"
    for name in ("silver/transactions", "silver/customer_states", "silver/inspection_decisions", "features"):
        if name in clean_table:
            canonical_name = name
            break

    subpath = f"lakehouse/fraud_detection/{canonical_name}"
    webhdfs_base = os.getenv("WEBHDFS_BASE", f"http://{settings.NAMENODE_HOST}:9870/webhdfs/v1")
    return {
        "canonical_name": canonical_name,
        "subpath": subpath,
        "hdfs_uri": f"{settings.HDFS_URL}/{subpath}",
        "webhdfs_dir": f"{webhdfs_base}/{subpath}",
        "webhdfs_log": f"{webhdfs_base}/{subpath}/_delta_log",
    }

def get_delta_table(table_name: str = "gold/risk_scores", version: Optional[int] = None) -> DeltaTable:
    paths = resolve_table_paths(table_name)
    uri = paths["hdfs_uri"]
    if version is not None:
        return DeltaTable(uri, version=version)
    return DeltaTable(uri)
