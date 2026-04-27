from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth import TokenMiddleware
from app.mcp_server import mcp
from app.routers import history, rastreamento, ui

limiter = Limiter(key_func=get_remote_address)

# FastMCP — endpoint will live at /mcp (no sub-mount, avoids 307 redirect)
_mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(
    title="Correios Rastreamento",
    description=(
        "Rastreia objetos dos Correios com histórico completo de eventos e resolução automática "
        "de CAPTCHA via rede neural local.\n\n"
        "**Autenticação:** quando `API_TOKEN` está configurado, todos os endpoints (exceto `/`) "
        "exigem `Authorization: Bearer <token>`. Use o botão **Authorize** acima para informar o token."
    ),
    version="1.0.0",
    lifespan=_mcp_app.lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)


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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(TokenMiddleware)


# REST routers — all defined before mount so they aren't swallowed by the "/" catch-all
@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Verifica se o servidor está no ar.",
    responses={200: {"content": {"application/json": {"example": {"status": "ok"}}}}},
)
async def health():
    return {"status": "ok"}


app.include_router(ui.router)
app.include_router(history.router)
app.include_router(rastreamento.router)

Instrumentator().instrument(app).expose(app, include_in_schema=False)

app.mount("/", _mcp_app)
