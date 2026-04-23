import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_TOKEN: str = os.getenv("API_TOKEN", "")

_ALWAYS_PUBLIC = {"/", "/health"}
_DEV_PUBLIC = {"/docs", "/redoc", "/openapi.json"}


class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        env = os.getenv("ENV", "development")
        public = _ALWAYS_PUBLIC | (_DEV_PUBLIC if env == "development" else set())
        if path in public:
            return await call_next(request)
        token = os.getenv("API_TOKEN", "")
        if token:
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] != token:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
