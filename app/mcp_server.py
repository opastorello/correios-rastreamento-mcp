import re as _re
from typing import List

from fastmcp import FastMCP

from app import metrics as _m
from app.services import correios

mcp = FastMCP("correios-rastreamento")

_CODE_RE = _re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$')


@mcp.tool
async def rastrear_objeto(codigo: str) -> dict:
    """Rastreia um objeto pelo código (ex: AA000000000BR)"""
    codigo = codigo.strip().upper()
    if not _CODE_RE.match(codigo):
        _m.correios_mcp_calls_total.labels(tool="rastrear_objeto", result="invalid").inc()
        return {"erro": True, "mensagem": f"Código inválido '{codigo}'. Formato esperado: 2 letras + 9 dígitos + 2 letras (ex: AA000000000BR)"}
    result = await correios.rastrear_objeto(codigo)
    label = "not_found" if result.get("erro") else "success"
    _m.correios_mcp_calls_total.labels(tool="rastrear_objeto", result=label).inc()
    return result


@mcp.tool
async def rastrear_multiplos(codigos: List[str]) -> object:
    """Rastreia até 20 objetos de uma vez (ex: ["AA000000000BR", "AA000000001BR"])"""
    codigos = [c.strip().upper() for c in codigos]
    invalid = [c for c in codigos if not _CODE_RE.match(c)]
    if invalid:
        amostra = ", ".join(invalid[:3]) + ("…" if len(invalid) > 3 else "")
        _m.correios_mcp_calls_total.labels(tool="rastrear_multiplos", result="invalid").inc()
        return {"erro": True, "mensagem": f"Código(s) inválido(s): {amostra}"}
    if len(codigos) > 20:
        _m.correios_mcp_calls_total.labels(tool="rastrear_multiplos", result="invalid").inc()
        raise ValueError("Máximo de 20 objetos por chamada")
    _m.correios_batch_size.observe(len(codigos))
    result = await correios.rastrear_multiplos(codigos)
    _m.correios_mcp_calls_total.labels(tool="rastrear_multiplos", result="success").inc()
    return result
