"""
Testes da API REST — todos os chamados ao Correios são mockados.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from contextlib import asynccontextmanager
    import app.auth as _auth
    _auth._TOKEN = ""  # garante que o client de teste roda sem autenticação
    from app.main import app

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    app.router.lifespan_context = _noop_lifespan
    return TestClient(app, raise_server_exceptions=True)


MOCK_OBJETO = {
    "codObjeto": "AA000000000BR",
    "tipoPostal": {"sigla": "AA", "descricao": "SEDEX", "categoria": "SEDEX", "tipo": "N"},
    "situacao": "E",
    "dtPrevista": "01/01/2026",
    "eventos": [
        {
            "codigo": "BDE",
            "descricaoWeb": "ENTREGUE",
            "descricaoFrontEnd": "ENTREGUE",
            "finalizador": "S",
            "dtHrCriado": {"date": "2026-01-01 10:00:00.000000", "timezone_type": 3, "timezone": "America/Sao_Paulo"},
            "unidade": {"tipo": "Unidade de Distribuição", "endereco": {"cidade": "SAO PAULO", "uf": "SP"}},
        }
    ],
}

MOCK_ERRO = {"erro": True, "mensagem": "Objeto não encontrado na base de dados dos Correios."}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /rastreamento/objeto
# ---------------------------------------------------------------------------

def test_rastrear_objeto_sucesso(client):
    with patch("app.services.correios.rastrear_objeto", new=AsyncMock(return_value=MOCK_OBJETO)):
        r = client.post("/rastreamento/objeto", json={"codigo": "AA000000000BR"})
    assert r.status_code == 200
    data = r.json()
    assert data["codObjeto"] == "AA000000000BR"
    assert data["situacao"] == "E"
    assert len(data["eventos"]) == 1
    assert data["eventos"][0]["descricaoWeb"] == "ENTREGUE"


def test_rastrear_objeto_nao_encontrado(client):
    with patch("app.services.correios.rastrear_objeto", new=AsyncMock(return_value=MOCK_ERRO)):
        r = client.post("/rastreamento/objeto", json={"codigo": "XX000000000BR"})
    assert r.status_code == 200
    assert r.json()["erro"] is True


def test_rastrear_objeto_payload_invalido(client):
    r = client.post("/rastreamento/objeto", json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /rastreamento/multiplos
# ---------------------------------------------------------------------------

def test_rastrear_multiplos_sucesso(client):
    codigos = ["AA000000000BR", "AA000000001BR"]
    mock_result = {c: MOCK_OBJETO for c in codigos}
    with patch("app.services.correios.rastrear_multiplos", new=AsyncMock(return_value=mock_result)):
        r = client.post("/rastreamento/multiplos", json={"codigos": codigos})
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == set(codigos)
    assert data["AA000000000BR"]["situacao"] == "E"


def test_rastrear_multiplos_limite_20(client):
    codigos = [f"AA{i:09d}BR" for i in range(21)]
    r = client.post("/rastreamento/multiplos", json={"codigos": codigos})
    assert r.status_code == 400


def test_rastrear_multiplos_payload_invalido(client):
    r = client.post("/rastreamento/multiplos", json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

def test_auth_sem_api_token_configurado(client):
    """Sem API_TOKEN no ambiente — todas as rotas são livres."""
    r = client.get("/health")
    assert r.status_code == 200

    with patch("app.services.correios.rastrear_objeto", new=AsyncMock(return_value=MOCK_OBJETO)):
        r = client.post("/rastreamento/objeto", json={"codigo": "AA000000000BR"})
    assert r.status_code == 200


def test_auth_com_api_token(monkeypatch):
    """Com API_TOKEN definido — exige Bearer token correto."""
    import app.auth as _auth
    monkeypatch.setattr(_auth, "_TOKEN", "test-secret")

    from fastapi import FastAPI
    from app.auth import TokenMiddleware
    from app.routers import rastreamento

    test_app = FastAPI()
    test_app.add_middleware(TokenMiddleware)
    test_app.include_router(rastreamento.router)

    @test_app.get("/health")
    async def health():
        return {"status": "ok"}

    with TestClient(test_app) as c:
        # health sempre público
        assert c.get("/health").status_code == 200

        # sem token → 401
        r = c.post("/rastreamento/objeto", json={"codigo": "AA000000000BR"})
        assert r.status_code == 401

        # token errado → 401
        r = c.post("/rastreamento/objeto",
                   json={"codigo": "AA000000000BR"},
                   headers={"Authorization": "Bearer errado"})
        assert r.status_code == 401

        # token correto → passa para o handler
        with patch("app.services.correios.rastrear_objeto", new=AsyncMock(return_value=MOCK_OBJETO)):
            r = c.post("/rastreamento/objeto",
                       json={"codigo": "AA000000000BR"},
                       headers={"Authorization": "Bearer test-secret"})
        assert r.status_code == 200
