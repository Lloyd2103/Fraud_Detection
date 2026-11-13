from pydantic import BaseModel

class LatencyStatsResponse(BaseModel):
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    max_latency_ms: int
    sla_limit_ms: int
    sla_compliance_rate: float
    sla_compliance_rate_pct: float
    sla_2s_rate: float
    sla_5s_rate: float
    total_measured_alerts: int
    status: str
    status_reason: str

