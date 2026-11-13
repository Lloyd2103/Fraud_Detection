from typing import Dict, Any
from pydantic import BaseModel

class DeltaConfigResponse(BaseModel):
    spark_version: str
    delta_version: str
    target_table: str
    retention_period: str
    auto_optimize_optimizeWrite: str
    auto_optimize_autoCompact: str
    enableChangeDataFeed: str
    deletedFileRetentionDuration: str
    infrastructure: Dict[str, Any]
    medallion_layers: Dict[str, Any]
    checkpoints: Dict[str, Any]

