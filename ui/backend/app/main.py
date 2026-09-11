# Entry application file running FastAPI server with static frontend serving & CORS configuration
import os
import sys

# Ensure official PySpark from SPARK_HOME takes precedence over user site-packages
spark_home = os.getenv("SPARK_HOME", "/home/master/spark")
py4j_zip = os.path.join(spark_home, "python/lib/py4j-0.10.9.7-src.zip")
pyspark_path = os.path.join(spark_home, "python")

if os.path.exists(pyspark_path) and pyspark_path not in sys.path:
    sys.path.insert(0, py4j_zip)
    sys.path.insert(0, pyspark_path)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.schemas.alert_schema import *
from app.routers import alerts
from app.core.spark_session import SparkClientManager

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Pre-initialize PySpark singleton session during application startup
    try:
        SparkClientManager.get_spark()
        print("[Spark] Singleton Session pre-initialized successfully.")
    except Exception as exc:
        print(f"[Spark Startup Warning] {exc}")

# API Router Registration
app.include_router(alerts.router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "HEALTHY"}

# WebSocket endpoint for real-time alert streaming
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

# Serve Human-in-the-Loop Investigation UI Frontend at Root (/)
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Set reload=False to avoid PySpark JVM process forks in WatchFiles reloader
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)