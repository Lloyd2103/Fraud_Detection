"""
System constants.
Risk thresholds, SLA targets and the daily alert capacity live in app.config.settings
(single source of truth). Only cache TTLs and the supported table list are defined here.
"""

SUPPORTED_TABLES = {
    "features",
    "silver/transactions",
    "silver/customer_states",
    "silver/inspection_decisions",
    "gold/risk_scores",
}

# Cache TTLs (seconds)
CACHE_TTL_HEALTH = 10.0
CACHE_TTL_SUMMARY = 5.0
CACHE_TTL_VERDICT_STATS = 30.0
CACHE_TTL_LATENCY = 60.0
CACHE_TTL_TIME_TRAVEL = 600.0
