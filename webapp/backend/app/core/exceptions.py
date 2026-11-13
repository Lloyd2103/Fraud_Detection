"""
Custom Business Exceptions & Exception Handlers
Enforces clean boundary: services raise domain/business exceptions without importing FastAPI.
"""
from typing import Any

class AppException(Exception):
    def __init__(self, status_code: int = 400, detail: Any = "Bad Request"):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail

class BadRequestError(AppException):
    def __init__(self, detail: Any = "Invalid request"):
        super().__init__(status_code=400, detail=detail)

class UnauthorizedError(AppException):
    def __init__(self, detail: Any = "Authentication required. Please sign in."):
        super().__init__(status_code=401, detail=detail)

class PermissionDeniedError(AppException):
    def __init__(self, detail: Any = "Access denied: unauthorized"):
        super().__init__(status_code=403, detail=detail)

class NotFoundError(AppException):
    def __init__(self, detail: Any = "Resource not found"):
        super().__init__(status_code=404, detail=detail)

class ConflictError(AppException):
    def __init__(self, detail: Any = "Resource conflict"):
        super().__init__(status_code=409, detail=detail)

class TooManyRequestsError(AppException):
    def __init__(self, detail: Any = "Too many requests. Please try again later."):
        super().__init__(status_code=429, detail=detail)

class GatewayTimeoutError(AppException):
    def __init__(self, detail: Any = "Gateway timeout"):
        super().__init__(status_code=504, detail=detail)

class ServiceUnavailableError(AppException):
    def __init__(self, detail: Any = "Service unavailable"):
        super().__init__(status_code=503, detail=detail)

def register_exception_handlers(app):
    from fastapi.responses import JSONResponse
    from slowapi.errors import RateLimitExceeded

    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}. Please try again later."}
        )
