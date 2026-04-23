from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

from app.auth import TokenMiddleware  # noqa: E402
from app.mcp_server import mcp  # noqa: E402
from app.routers import history, rastreamento, ui  # noqa: E402

limiter = Limiter(key_func=get_remote_address)

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


@app.get(
    "/health",
    tags=["status"],
    summary="Health check",
    description="Verifica se o servidor está no ar. Em `ENV=production` exige token.",
    responses={200: {"content": {"application/json": {"example": {"status": "ok"}}}}},
)
def health():
    return {"status": "ok"}


app.include_router(ui.router)
app.include_router(history.router)
app.include_router(rastreamento.router)

app.mount("/", _mcp_app)
