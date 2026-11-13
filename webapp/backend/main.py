"""
Real-Time Fraud Detection Web Application Backend
Complies with DeTai_2.pdf specifications (Lakehouse, Delta Lake, FastAPI, WebSocket).
Modularized Architecture (Step 17).
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config.settings import settings
from app.database import init_db
from app.core.middleware import setup_middleware
from app.core.exceptions import register_exception_handlers
from prometheus_fastapi_instrumentator import Instrumentator

# Import module routers
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.alerts.router import router as alerts_router
from app.modules.verdicts.router import router as verdicts_router
from app.modules.transactions.router import router as transactions_router
from app.modules.fraud_summary.router import router as fraud_summary_router
from app.modules.latency.router import router as latency_router
from app.modules.delta_config.router import router as delta_config_router
from app.modules.health.router import router as health_router
from app.modules.model_governance.router import router as model_governance_router
from app.modules.time_travel.router import router as time_travel_router
from app.modules.realtime.router import router as realtime_router

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize CockroachDB tables (idempotent)
    init_db()
    print("[Startup] CockroachDB tables initialized (system_db)")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Real-Time Credit Card Fraud Detection Platform",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware & Exception Handlers
setup_middleware(app)
register_exception_handlers(app)

# Prometheus APM Metrics (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)

# Mount Modular API Routers under /api
app.include_router(alerts_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(verdicts_router, prefix="/api")
app.include_router(fraud_summary_router, prefix="/api")
app.include_router(latency_router, prefix="/api")
app.include_router(delta_config_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(model_governance_router, prefix="/api")
app.include_router(time_travel_router, prefix="/api")

# Mount Realtime WebSocket Router (has /ws/alerts)
app.include_router(realtime_router)

# Mount React built assets
if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets")


@app.get("/")
@app.get("/{full_path:path}")
def serve_spa(full_path: str = ""):
    if (
        full_path.startswith("api")
        or full_path.startswith("ws")
        or full_path.startswith("docs")
        or full_path.startswith("redoc")
        or full_path.startswith("openapi.json")
        or full_path.startswith("metrics")
    ):
        raise HTTPException(status_code=404, detail="Not Found")
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Fraud Detection API running"}


if __name__ == "__main__":
    import uvicorn

    reload_flag = os.getenv("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("main:app", host=settings.SERVER_HOST, port=settings.SERVER_PORT, reload=reload_flag)
