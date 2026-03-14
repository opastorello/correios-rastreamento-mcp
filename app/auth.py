import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/docs", "/redoc", "/openapi.json"}:
            return await call_next(request)
        token = os.getenv("API_TOKEN", "")
        if token:
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] != token:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
