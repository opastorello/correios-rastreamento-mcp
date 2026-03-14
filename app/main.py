import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.auth import TokenMiddleware  # noqa: E402
from app.mcp_server import mcp  # noqa: E402
from app.routers import rastreamento  # noqa: E402

_mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _mcp_app.lifespan(app):
        yield


app = FastAPI(title="correios-rastreamento", lifespan=lifespan)

if os.getenv("API_TOKEN"):
    app.add_middleware(TokenMiddleware)

app.include_router(rastreamento.router)


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/mcp", _mcp_app)
