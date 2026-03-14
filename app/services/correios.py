"""
Serviço de rastreamento dos Correios.

Fluxo por consulta (objeto único):
  1. GET index.php → session cookie (RASTREAMENTO + INGRESSCOOKIE)
  2. GET securimage_show.php → imagem CAPTCHA (215x80px, 4-6 chars lowercase alfanumérico)
  3. Resolve CAPTCHA com CRNN local (captcha_model.pt) ou ddddocr como fallback
  4. GET resultado.php?objeto={code}&captcha={text}&mqs=S → JSON
  5. Retry até MAX_RETRIES se CAPTCHA inválido

Fluxo para múltiplos objetos (até 20):
  1-3. Igual ao acima
  4. GET rastroMulti.php?objeto={cod1cod2...}&captcha={text} → JSON com 'entregue' e 'transito'
     Códigos concatenados sem separador (cada código tem 13 chars)
  5. Retry até MAX_RETRIES se CAPTCHA inválido
  — 1 CAPTCHA para até 20 objetos (em vez de N requests individuais)
"""
from typing import Any

from curl_cffi import requests as cffi_requests
from starlette.concurrency import run_in_threadpool

_BASE_URL = "https://rastreamento.correios.com.br/app"
_CAPTCHA_URL = "https://rastreamento.correios.com.br/core/securimage/securimage_show.php"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": f"{_BASE_URL}/index.php",
}
MAX_RETRIES = 4

def _solve_captcha(image_bytes: bytes) -> str:
    from app.captcha.predictor import predict
    return predict(image_bytes).strip()


def _is_captcha_error(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    erro = data.get("erro")
    # API retorna "erro": "true" (string) ou "erro": true (bool)
    erro_flag = erro is True or str(erro).lower() == "true"
    return erro_flag and "captcha" in data.get("mensagem", "").lower()


def _fetch_captcha(session) -> bytes:
    session.get(f"{_BASE_URL}/index.php", headers=_HEADERS, timeout=30)
    resp = session.get(_CAPTCHA_URL, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.content


def _rastrear_sync(codigo: str) -> dict:
    session = cffi_requests.Session(impersonate="chrome124")
    for _ in range(MAX_RETRIES):
        image_bytes = _fetch_captcha(session)
        captcha_text = _solve_captcha(image_bytes)
        resp = session.get(
            f"{_BASE_URL}/resultado.php",
            params={"objeto": codigo, "captcha": captcha_text, "mqs": "S"},
            headers=_HEADERS,
            timeout=30,
        )
        data = resp.json()
        if _is_captcha_error(data):
            continue
        return data
    return {"erro": True, "mensagem": f"CAPTCHA inválido após {MAX_RETRIES} tentativas"}


def _rastrear_multiplos_sync(codigos: list) -> dict:
    session = cffi_requests.Session(impersonate="chrome124")
    objeto_param = "".join(codigos)
    for _ in range(MAX_RETRIES):
        image_bytes = _fetch_captcha(session)
        captcha_text = _solve_captcha(image_bytes)
        resp = session.get(
            f"{_BASE_URL}/rastroMulti.php",
            params={"objeto": objeto_param, "captcha": captcha_text},
            headers=_HEADERS,
            timeout=30,
        )
        data = resp.json()
        if _is_captcha_error(data):
            continue
        if isinstance(data, dict) and data.get("erro"):
            return {c: data for c in codigos}
        # Monta dict por código a partir de 'entregue' e 'transito'
        results = {}
        for group in ("entregue", "transito"):
            for item in data.get(group, []):
                # cod_objeto_ é o código sem formatação (ex: AA000000000BR)
                cod = item.get("cod_objeto_", "").replace(" ", "")
                if cod and item.get("objeto"):
                    results[cod] = item["objeto"]
        for c in codigos:
            if c not in results:
                results[c] = {"erro": True, "mensagem": "Objeto não encontrado na base de dados dos Correios."}
        return results
    return {c: {"erro": True, "mensagem": f"CAPTCHA inválido após {MAX_RETRIES} tentativas"} for c in codigos}


async def rastrear_objeto(codigo: str) -> dict:
    return await run_in_threadpool(_rastrear_sync, codigo)


async def rastrear_multiplos(codigos: list) -> dict:
    return await run_in_threadpool(_rastrear_multiplos_sync, codigos)
