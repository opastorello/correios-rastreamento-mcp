import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv()

from app.auth import TokenMiddleware  # noqa: E402
from app.mcp_server import mcp  # noqa: E402
from app.routers import history, rastreamento, ui  # noqa: E402
from app.routers.rastreamento import limiter  # noqa: E402

_mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _mcp_app.lifespan(app):
        yield


app = FastAPI(
    title="Correios Rastreamento",
    description="API REST e MCP para rastreamento de objetos dos Correios com CAPTCHA solver CRNN local.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(TokenMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(rastreamento.router)
app.include_router(history.router)
app.include_router(ui.router)


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "Token"}
    }
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict):
                operation["security"] = [{"BearerAuth": []}, {}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi


@app.get(
    "/health",
    summary="Health check",
    description='Verifica se o servidor está online. Sempre retorna `{"status": "ok"}`. Rota pública em desenvolvimento.',
    tags=["status"],
    responses={200: {"content": {"application/json": {"example": {"status": "ok"}}}}},
)
def health():
    return {"status": "ok"}


app.mount("/mcp", _mcp_app)
