from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import config as _cfg
from app import metrics as _m
from app.services import correios

limiter = Limiter(key_func=get_remote_address)

_EXAMPLE_OBJETO = {
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

_EXAMPLE_ERRO = {"erro": True, "mensagem": "Objeto não encontrado na base de dados dos Correios."}

_EXAMPLE_MULTIPLOS = {
    "AA000000000BR": _EXAMPLE_OBJETO,
    "AA000000001BR": _EXAMPLE_OBJETO,
}

router = APIRouter(prefix="/rastreamento", tags=["rastreamento"])


class ObjetoRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {"codigo": "AA000000000BR"}}}
    codigo: str = Field(..., description="Código de rastreamento do objeto (ex: AA000000000BR)", examples=["AA000000000BR"])


class MultiplosRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {"codigos": ["AA000000000BR", "AA000000001BR"]}}}
    codigos: List[str] = Field(..., description="Lista de códigos de rastreamento (máximo 20)", examples=[["AA000000000BR", "AA000000001BR"]])


@router.post(
    "/objeto",
    summary="Rastreia um objeto pelo código",
    description=(
        "Consulta os Correios para obter o histórico completo de eventos de um objeto. "
        "Resolve o CAPTCHA automaticamente via CRNN local (99.62% de acurácia). "
        "Retorna código, tipo postal, situação, data prevista e todos os eventos."
    ),
    responses={200: {"content": {"application/json": {"example": _EXAMPLE_OBJETO}}}},
)
@limiter.limit(_cfg.RATE_LIMIT_OBJETO)
async def rastrear_objeto(request: Request, body: ObjetoRequest):
    return await correios.rastrear_objeto(body.codigo)


@router.post(
    "/multiplos",
    summary="Rastreia até 20 objetos em paralelo",
    description=(
        "Consulta os Correios para múltiplos objetos usando um único CAPTCHA. "
        "Os códigos são enviados concatenados, economizando resolução de CAPTCHA. "
        "Máximo de 20 objetos por requisição."
    ),
    responses={200: {"content": {"application/json": {"example": _EXAMPLE_MULTIPLOS}}}},
)
@limiter.limit(_cfg.RATE_LIMIT_MULTIPLOS)
async def rastrear_multiplos(request: Request, body: MultiplosRequest):
    if len(body.codigos) > 20:
        raise HTTPException(status_code=400, detail="Máximo de 20 objetos por requisição")
    _m.correios_batch_size.observe(len(body.codigos))
    return await correios.rastrear_multiplos(body.codigos)
