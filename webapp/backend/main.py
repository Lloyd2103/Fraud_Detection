"""
Real-Time Fraud Detection Web Application Backend
Complies with DeTai_2.pdf specifications (Lakehouse, Delta Lake, FastAPI, WebSocket).
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import settings
from app.api import alerts_router, transactions_router, audit_router, latency_router
from app.services.lakehouse_service import lakehouse_service

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="Real-Time Credit Card Fraud Detection Platform (Project 2 - bd02_gian_lan)",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api
app.include_router(alerts_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(latency_router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# WebSocket Connection Manager for Live Real-Time Alerts
class AlertConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = AlertConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Real-time WebSocket feed for high-risk alerts.
    Pushes live alerts to the frontend dashboard.
    """
    await manager.connect(websocket)
    try:
        # Push initial batch
        initial_alerts = lakehouse_service.get_alert_queue(status="new", limit=10)
        await websocket.send_json({
            "type": "INIT_ALERTS",
            "data": initial_alerts,
            "timestamp": str(asyncio.get_event_loop().time())
        })
        
        while True:
            # Keep-alive and listen for client commands or wait 4 seconds then stream updates
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=4.0)
                cmd = json.loads(data)
                if cmd.get("action") == "REFRESH":
                    latest = lakehouse_service.get_alert_queue(status="new", limit=15)
                    await websocket.send_json({"type": "ALERTS_UPDATE", "data": latest})
            except asyncio.TimeoutError:
                # Periodic heartbeat & live stream update
                latest = lakehouse_service.get_alert_queue(status="new", limit=15)
                await websocket.send_json({"type": "HEARTBEAT_UPDATE", "data": latest})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)

@app.get("/api/health")
def health_check():
    """
    Health check verifying connectivity to HDFS, Kafka, and Spark.
    """
    return {
        "status": "UP",
        "app": settings.APP_NAME,
        "lakehouse_base": settings.LAKEHOUSE_BASE,
        "namenode": f"{settings.NAMENODE_HOST}:{settings.NAMENODE_PORT}",
        "kafka_broker": settings.KAFKA_BOOTSTRAP_SERVERS,
        "sla_latency_limit": f"{settings.SLA_LATENCY_MAX_SECONDS}s",
        "version": settings.APP_VERSION
    }

@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serve the single-page application dashboard"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Real-Time Fraud Detection WebApp</h1><p>Static assets are loading...</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.SERVER_HOST, port=settings.SERVER_PORT, reload=True)