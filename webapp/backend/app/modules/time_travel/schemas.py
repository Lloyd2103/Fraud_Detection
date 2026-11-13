from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class CommitItemOut(BaseModel):
    version: int
    timestamp: str
    operation: str
    engine: Optional[str] = None
    userName: Optional[str] = None
    operationParameters: Optional[Dict[str, Any]] = None

class TimeTravelResponse(BaseModel):
    status: str
    table: str
    delta_version: int
    total_records: int
    checksum: Optional[str] = None
    sample_data: Optional[List[Dict[str, Any]]] = []

