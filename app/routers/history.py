import json
import os
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from app import config as _cfg

router = APIRouter(prefix="/history", tags=["history"])

_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")
_lock = threading.Lock()
_RETENTION_DAYS = _cfg.HISTORY_RETENTION_DAYS
_TZ = ZoneInfo(_cfg.APP_TIMEZONE)

_EXAMPLE_ENTRY = {
    "codigo": "AA000000000BR",
    "status": "ENTREGUE",
    "entregue": True,
    "consultas": 3,
    "primeira_consulta": "2026-04-20T10:30:00-03:00",
    "ultima_consulta": "2026-04-23T14:22:10-03:00",
    "ultima_duracao_s": 1.5,
}


def _load() -> dict:
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)
    if not os.path.exists(_FILE):
        return {}
    with open(_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _persist(data: dict):
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _purge_old(data: dict) -> dict:
    if _RETENTION_DAYS <= 0:
        return data
    cutoff = (datetime.now(_TZ) - timedelta(days=_RETENTION_DAYS)).isoformat()
    return {k: v for k, v in data.items() if v.get("ultima_consulta", "") >= cutoff}


class SaveRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {"codigo": "AA000000000BR", "status": "ENTREGUE", "entregue": True, "duracao_segundos": 1.5}}}
    codigo: str = Field(..., description="Código de rastreamento do objeto", examples=["AA000000000BR"])
    status: str | None = Field(None, description="Último status do objeto (ex: ENTREGUE, EM TRÂNSITO)", examples=["ENTREGUE"])
    entregue: bool | None = Field(None, description="Indica se o objeto foi entregue", examples=[True])
    duracao_segundos: float | None = Field(None, description="Tempo de resposta da consulta em segundos", examples=[1.5])


@router.post(
    "/save",
    summary="Salva ou atualiza uma entrada no histórico",
    description="Registra a consulta de um objeto no histórico server-side. Se o código já existe, incrementa o contador e atualiza status, entrega e duração. Entradas são retidas por `HISTORY_RETENTION_DAYS` dias.",
    responses={200: {"content": {"application/json": {"example": {"ok": True}}}}},
)
def save(entry: SaveRequest):
    key = entry.codigo.upper().strip()
    now = datetime.now(_TZ).isoformat()
    with _lock:
        data = _purge_old(_load())
        if key in data:
            data[key]["consultas"] += 1
            data[key]["ultima_consulta"] = now
            if entry.status:
                data[key]["status"] = entry.status
            if entry.entregue is not None:
                data[key]["entregue"] = entry.entregue
            if entry.duracao_segundos is not None:
                data[key]["ultima_duracao_s"] = round(entry.duracao_segundos, 1)
        else:
            data[key] = {
                "codigo": entry.codigo.upper().strip(),
                "status": entry.status,
                "entregue": entry.entregue,
                "consultas": 1,
                "primeira_consulta": now,
                "ultima_consulta": now,
                "ultima_duracao_s": round(entry.duracao_segundos, 1) if entry.duracao_segundos else None,
            }
        _persist(data)
    return {"ok": True}


@router.get(
    "/",
    summary="Lista o histórico de rastreamentos",
    description="Retorna todas as entradas do histórico server-side, ordenadas pela consulta mais recente. Entradas expiradas pelo período de retenção são removidas automaticamente.",
    responses={200: {"content": {"application/json": {"example": {"entries": [_EXAMPLE_ENTRY], "total": 1}}}}},
)
def get_all():
    with _lock:
        data = _purge_old(_load())
    entries = sorted(data.values(), key=lambda x: x.get("ultima_consulta", ""), reverse=True)
    return {"entries": entries, "total": len(entries)}


@router.delete(
    "/",
    summary="Limpa todo o histórico",
    description="Remove permanentemente todas as entradas do histórico server-side.",
    responses={200: {"content": {"application/json": {"example": {"ok": True}}}}},
)
def clear_all():
    with _lock:
        _persist({})
    return {"ok": True}


@router.delete(
    "/{codigo_raw}",
    summary="Remove uma entrada do histórico",
    description="Remove do histórico a entrada correspondente ao código de rastreamento informado.",
    responses={200: {"content": {"application/json": {"example": {"ok": True}}}}},
)
def delete_entry(
    codigo_raw: str = Path(..., description="Código de rastreamento a remover", examples=["AA000000000BR"]),
):
    key = codigo_raw.upper().strip()
    with _lock:
        data = _load()
        data.pop(key, None)
        _persist(data)
    return {"ok": True}
