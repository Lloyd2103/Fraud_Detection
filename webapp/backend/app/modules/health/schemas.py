from typing import Optional
from pydantic import BaseModel

class HealthCheckOut(BaseModel):
    status: str
    app: str
    lakehouse_base: str
    namenode: str
    kafka_broker: str
    sla_latency_limit: str
    version: str

class PipelineHealthOut(BaseModel):
    kafka_reachable: bool
    last_alert_age_seconds: Optional[int] = None
    detector_state: str
    checked_at: str

