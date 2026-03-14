from typing import List

from fastmcp import FastMCP

from app.services import correios

mcp = FastMCP("correios-rastreamento")


@mcp.tool()
async def rastrear_objeto(codigo: str) -> dict:
    """Rastreia um objeto pelo código (ex: AA000000000BR)"""
    return await correios.rastrear_objeto(codigo)


@mcp.tool()
async def rastrear_multiplos(codigos: List[str]) -> object:
    """Rastreia até 20 objetos de uma vez (ex: ["AA000000000BR", "AA000000001BR"])"""
    if len(codigos) > 20:
        raise ValueError("Máximo de 20 objetos por chamada")
    return await correios.rastrear_multiplos(codigos)
