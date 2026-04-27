import re as _re
from typing import List

from fastmcp import FastMCP

from app.services import correios

mcp = FastMCP("correios-rastreamento")

_CODE_RE = _re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$')


@mcp.tool
async def rastrear_objeto(codigo: str) -> dict:
    """Rastreia um objeto pelo código (ex: AA000000000BR)"""
    codigo = codigo.strip().upper()
    if not _CODE_RE.match(codigo):
        return {"erro": True, "mensagem": f"Código inválido '{codigo}'. Formato esperado: 2 letras + 9 dígitos + 2 letras (ex: AA000000000BR)"}
    return await correios.rastrear_objeto(codigo)


@mcp.tool
async def rastrear_multiplos(codigos: List[str]) -> object:
    """Rastreia até 20 objetos de uma vez (ex: ["AA000000000BR", "AA000000001BR"])"""
    codigos = [c.strip().upper() for c in codigos]
    invalid = [c for c in codigos if not _CODE_RE.match(c)]
    if invalid:
        amostra = ", ".join(invalid[:3]) + ("…" if len(invalid) > 3 else "")
        return {"erro": True, "mensagem": f"Código(s) inválido(s): {amostra}"}
    if len(codigos) > 20:
        raise ValueError("Máximo de 20 objetos por chamada")
    return await correios.rastrear_multiplos(codigos)
