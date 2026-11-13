"""
Application middleware configuration.
CORS is only enabled for origins listed in CORS_ALLOW_ORIGINS (comma-separated).
When the variable is empty the app is same-origin only (the Vite dev proxy and the
built frontend served by FastAPI are both same-origin).
"""
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.config.settings import settings
from app.core.limiter import limiter


def setup_middleware(app):
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    origins = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
