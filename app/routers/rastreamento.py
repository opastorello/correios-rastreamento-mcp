from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import correios

router = APIRouter(prefix="/rastreamento", tags=["rastreamento"])


class ObjetoRequest(BaseModel):
    codigo: str


class MultiplosRequest(BaseModel):
    codigos: List[str]


@router.post("/objeto")
async def rastrear_objeto(req: ObjetoRequest):
    return await correios.rastrear_objeto(req.codigo)


@router.post("/multiplos")
async def rastrear_multiplos(req: MultiplosRequest):
    if len(req.codigos) > 20:
        raise HTTPException(status_code=400, detail="Máximo de 20 objetos por requisição")
    return await correios.rastrear_multiplos(req.codigos)
