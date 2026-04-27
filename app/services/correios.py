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
import threading
import time
from typing import Any

from curl_cffi import requests as cffi_requests
from starlette.concurrency import run_in_threadpool

from app import config as _cfg
from app import metrics as _m

_BASE_URL = "https://rastreamento.correios.com.br/app"
_CAPTCHA_URL = "https://rastreamento.correios.com.br/core/securimage/securimage_show.php"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": f"{_BASE_URL}/index.php",
}

# Limita conexões simultâneas aos Correios independente de quantos usuários estão consultando
_CORREIOS_SEMAPHORE = threading.Semaphore(_cfg.MAX_CONCURRENT)


def _solve_captcha(image_bytes: bytes) -> str:
    from app.captcha.predictor import predict
    return predict(image_bytes).strip()


def _is_captcha_error(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    erro = data.get("erro")
    erro_flag = erro is True or str(erro).lower() == "true"
    return erro_flag and "captcha" in data.get("mensagem", "").lower()


def _fetch_captcha(session) -> bytes:
    session.get(f"{_BASE_URL}/index.php", headers=_HEADERS, timeout=_cfg.HTTP_TIMEOUT)
    resp = session.get(_CAPTCHA_URL, headers=_HEADERS, timeout=_cfg.CAPTCHA_TIMEOUT)
    resp.raise_for_status()
    return resp.content


def _rastrear_sync(codigo: str) -> dict:
    _m.correios_concurrent_queries.inc()
    try:
        with _CORREIOS_SEMAPHORE:
            return _rastrear_com_sessao(codigo)
    finally:
        _m.correios_concurrent_queries.dec()


def _rastrear_com_sessao(codigo: str) -> dict:
    session = cffi_requests.Session(impersonate="chrome124")
    attempts = 0
    t_start = time.time()

    for _ in range(_cfg.MAX_RETRIES):
        try:
            t_captcha = time.time()
            _m.correios_captcha_attempts_total.inc()
            attempts += 1

            image_bytes = _fetch_captcha(session)
            captcha_text = _solve_captcha(image_bytes)
            _m.correios_captcha_duration_seconds.observe(time.time() - t_captcha)

            resp = session.get(
                f"{_BASE_URL}/resultado.php",
                params={"objeto": codigo, "captcha": captcha_text, "mqs": "S"},
                headers=_HEADERS,
                timeout=_cfg.HTTP_TIMEOUT,
            )
            data = resp.json()

            if _is_captcha_error(data):
                _m.correios_captcha_result_total.labels(result="wrong").inc()
                continue

            _m.correios_captcha_result_total.labels(result="success").inc()
            _m.correios_captcha_retries_per_query.observe(attempts)
            _m.correios_query_duration_seconds.observe(time.time() - t_start)
            if data.get("erro"):
                _m.correios_queries_total.labels(type="single", result="not_found").inc()
                _m.correios_objects_total.labels(result="not_found").inc()
            else:
                _m.correios_queries_total.labels(type="single", result="success").inc()
                _m.correios_objects_total.labels(result="found").inc()
            return data

        except Exception as exc:
            _m.correios_captcha_result_total.labels(result="error").inc()
            err_type = "timeout" if "timeout" in str(exc).lower() else "connection"
            _m.correios_http_errors_total.labels(type=err_type).inc()
            continue

    _m.correios_captcha_retries_per_query.observe(attempts)
    _m.correios_queries_total.labels(type="single", result="captcha_failed").inc()
    _m.correios_objects_total.labels(result="error").inc()
    _m.correios_query_duration_seconds.observe(time.time() - t_start)
    return {"erro": True, "mensagem": f"CAPTCHA inválido após {_cfg.MAX_RETRIES} tentativas"}


def _rastrear_multiplos_sync(codigos: list) -> dict:
    _m.correios_concurrent_queries.inc()
    try:
        with _CORREIOS_SEMAPHORE:
            return _rastrear_multiplos_com_sessao(codigos)
    finally:
        _m.correios_concurrent_queries.dec()


def _rastrear_multiplos_com_sessao(codigos: list) -> dict:
    session = cffi_requests.Session(impersonate="chrome124")
    objeto_param = "".join(codigos)
    attempts = 0
    t_start = time.time()

    for _ in range(_cfg.MAX_RETRIES):
        try:
            t_captcha = time.time()
            _m.correios_captcha_attempts_total.inc()
            attempts += 1

            image_bytes = _fetch_captcha(session)
            captcha_text = _solve_captcha(image_bytes)
            _m.correios_captcha_duration_seconds.observe(time.time() - t_captcha)

            resp = session.get(
                f"{_BASE_URL}/rastroMulti.php",
                params={"objeto": objeto_param, "captcha": captcha_text},
                headers=_HEADERS,
                timeout=_cfg.HTTP_TIMEOUT,
            )
            data = resp.json()

            if _is_captcha_error(data):
                _m.correios_captcha_result_total.labels(result="wrong").inc()
                continue

            _m.correios_captcha_result_total.labels(result="success").inc()
            _m.correios_captcha_retries_per_query.observe(attempts)
            _m.correios_query_duration_seconds.observe(time.time() - t_start)

            if isinstance(data, dict) and data.get("erro"):
                _m.correios_queries_total.labels(type="batch", result="error").inc()
                _m.correios_objects_total.labels(result="error").inc(len(codigos))
                return {c: data for c in codigos}

            results = {}
            for group in ("entregue", "transito"):
                for item in data.get(group, []):
                    cod = item.get("cod_objeto_", "").replace(" ", "")
                    if cod and item.get("objeto"):
                        results[cod] = item["objeto"]
            for c in codigos:
                if c not in results:
                    results[c] = {"erro": True, "mensagem": "Objeto não encontrado na base de dados dos Correios."}

            found = sum(1 for v in results.values() if not v.get("erro"))
            not_found = len(results) - found
            _m.correios_objects_total.labels(result="found").inc(found)
            _m.correios_objects_total.labels(result="not_found").inc(not_found)
            _m.correios_queries_total.labels(type="batch", result="success").inc()
            return results

        except Exception as exc:
            _m.correios_captcha_result_total.labels(result="error").inc()
            err_type = "timeout" if "timeout" in str(exc).lower() else "connection"
            _m.correios_http_errors_total.labels(type=err_type).inc()
            continue

    _m.correios_captcha_retries_per_query.observe(attempts)
    _m.correios_queries_total.labels(type="batch", result="captcha_failed").inc()
    _m.correios_objects_total.labels(result="error").inc(len(codigos))
    _m.correios_query_duration_seconds.observe(time.time() - t_start)
    return {c: {"erro": True, "mensagem": f"CAPTCHA inválido após {_cfg.MAX_RETRIES} tentativas"} for c in codigos}


async def rastrear_objeto(codigo: str) -> dict:
    return await run_in_threadpool(_rastrear_sync, codigo)


async def rastrear_multiplos(codigos: list) -> dict:
    return await run_in_threadpool(_rastrear_multiplos_sync, codigos)
