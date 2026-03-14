"""
Coleta amostras rotuladas do CAPTCHA do Correios.

Fluxo por amostra:
  1. GET index.php → session cookie (RASTREAMENTO)
  2. GET securimage_show.php → imagem do CAPTCHA
  3. Resolve com CRNN (se disponível) ou ddddocr
  4. GET resultado.php?objeto={probe}&captcha={text}&mqs=S
  5. Se resposta != "Captcha inválido" → salva imagem com label

Uso:
    python -m app.captcha.collector --probe AA000000000BR --target 15000 --workers 8
    python -m app.captcha.collector --probe AA000000000BR --target 15000 --workers 8 --proxy-api http://host/api/v1/proxy/all --proxy-key APIKEY
"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path

from curl_cffi import requests as cffi_requests

_MODEL_PT = Path(__file__).parent / "captcha_model.pt"

try:
    import ddddocr as _ddddocr
    _ocr = _ddddocr.DdddOcr(show_ad=False)
except ImportError:
    _ocr = None

_BASE_URL = "https://rastreamento.correios.com.br/app"
_CAPTCHA_URL = "https://rastreamento.correios.com.br/core/securimage/securimage_show.php"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": f"{_BASE_URL}/index.php",
}

_DATA_DIR = Path(__file__).parent / "data"
_DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Proxy pool
# ---------------------------------------------------------------------------

_MAX_PROXY_FAILS = 3   # falhas consecutivas antes de banir o proxy
_PROXY_COOLDOWN = 60   # segundos de cooldown após 429


class _ProxyPool:
    """Pool de proxies com rotação round-robin, cooldown de 429 e blacklist automática."""

    def __init__(self):
        self._proxies: list[str] = []
        self._backup: list[str] = []              # cópia original para reset
        self._idx = 0
        self._lock = threading.Lock()
        self._fails: dict[str, int] = {}          # proxy → falhas consecutivas
        self._cooldown: dict[str, float] = {}     # proxy → timestamp de liberação
        self._api_url: str = ""
        self._api_key: str = ""

    _http_only: bool = False

    @staticmethod
    def _parse_items(items: list) -> list[str]:
        _SCHEME = {"http": "http", "https": "http", "socks4": "socks4", "socks5": "socks5"}
        proxies = []
        for p in items:
            ptype = p.get("type", "http").lower()
            if _ProxyPool._http_only and ptype not in ("http", "https"):
                continue
            scheme = _SCHEME.get(ptype)
            if scheme is None:
                continue
            host, port = p["host"], p["port"]
            user, pwd = p.get("username", ""), p.get("password", "")
            if user and pwd:
                url = f"{scheme}://{user}:{pwd}@{host}:{port}"
            else:
                url = f"{scheme}://{host}:{port}"
            proxies.append(url)
        return proxies

    def load_from_api(self, api_url: str, api_key: str) -> int:
        """Carrega proxies de uma API REST. Retorna quantidade carregada."""
        self._api_url = api_url
        self._api_key = api_key
        return self._fetch_and_reload(announce=True)

    def _fetch_and_reload(self, announce: bool = False) -> int:
        """Busca proxies da API e recarrega o pool. Chamado sem lock."""
        try:
            r = cffi_requests.get(
                self._api_url,
                params={"Status": "working", "SortBy": "ping", "PageNumber": 1, "PageSize": 1000},
                headers={"accept": "text/plain", "X-Api-Key": self._api_key},
                timeout=15,
            )
            proxies = self._parse_items(json.loads(r.text).get("items", []))
            with self._lock:
                self._proxies = proxies
                self._backup = list(proxies)
                self._fails.clear()
                self._cooldown.clear()
                self._idx = 0
            if announce:
                print(f"[proxy] {len(proxies)} proxies carregados", flush=True)
            else:
                print(f"[proxy] pool vazio — recarregados {len(proxies)} proxies da API", flush=True)
            return len(proxies)
        except Exception as e:
            print(f"[proxy] Falha ao recarregar da API: {e} — resetando bans", file=sys.stderr)
            self._reset_from_backup()
            return len(self._proxies)

    def _reset_from_backup(self):
        """Restaura o backup local, limpando bans e cooldowns."""
        with self._lock:
            self._proxies = list(self._backup)
            self._fails.clear()
            self._cooldown.clear()
            self._idx = 0
        print(f"[proxy] bans limpos — {len(self._proxies)} proxies restaurados do backup", flush=True)

    def next(self) -> str | None:
        with self._lock:
            if not self._proxies:
                return None
            now = time.time()
            # Percorre até encontrar um proxy fora do cooldown
            for _ in range(len(self._proxies)):
                proxy = self._proxies[self._idx % len(self._proxies)]
                self._idx += 1
                if self._cooldown.get(proxy, 0) <= now:
                    return proxy
            # Todos em cooldown — retorna o que sair mais cedo
            proxy = min(self._proxies, key=lambda p: self._cooldown.get(p, 0))
            return proxy

    def report_ok(self, proxy: str | None):
        if proxy is None:
            return
        with self._lock:
            self._fails.pop(proxy, None)
            self._cooldown.pop(proxy, None)

    def report_429(self, proxy: str | None):
        """Coloca o proxy em cooldown sem contar como falha."""
        if proxy is None:
            return
        with self._lock:
            self._cooldown[proxy] = time.time() + _PROXY_COOLDOWN

    def report_fail(self, proxy: str | None):
        if proxy is None:
            return
        reload_needed = False
        with self._lock:
            self._fails[proxy] = self._fails.get(proxy, 0) + 1
            if self._fails[proxy] >= _MAX_PROXY_FAILS and proxy in self._proxies:
                self._proxies.remove(proxy)
                del self._fails[proxy]
                print(f"[proxy] banido após {_MAX_PROXY_FAILS} falhas: "
                      f"{proxy.split('@')[-1] if '@' in proxy else proxy} "
                      f"(restam {len(self._proxies)})", file=sys.stderr, flush=True)
                if not self._proxies:
                    reload_needed = True
        if reload_needed:
            print("[proxy] pool esgotado — recarregando...", flush=True)
            if self._api_url:
                self._fetch_and_reload()
            else:
                self._reset_from_backup()

    def __len__(self):
        return len(self._proxies)


_proxy_pool = _ProxyPool()


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def _solve(image_bytes: bytes) -> str:
    if _MODEL_PT.exists():
        from app.captcha.predictor import predict
        return predict(image_bytes).strip()
    if _ocr is not None:
        return _ocr.classification(image_bytes).strip().lower()
    raise RuntimeError("Nenhum solver disponível (instale ddddocr ou treine o modelo)")


def _new_session(proxy: str | None = None) -> cffi_requests.Session:
    session = cffi_requests.Session(impersonate="chrome124")
    session.verify = False
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session


def _init_session(session) -> None:
    """Inicializa a sessão PHP (obtém cookie RASTREAMENTO). Chama apenas uma vez por sessão."""
    session.get(f"{_BASE_URL}/index.php", headers=_HEADERS, timeout=30)
    session._initialized = True


# ---------------------------------------------------------------------------
# Collection logic
# ---------------------------------------------------------------------------

def collect_one(session, probe: str):
    if not getattr(session, "_initialized", False):
        _init_session(session)
    captcha_resp = session.get(_CAPTCHA_URL, headers=_HEADERS, timeout=15)
    captcha_resp.raise_for_status()
    image_bytes = captcha_resp.content

    # Valida que é realmente uma imagem (proxy pode retornar HTML de erro)
    try:
        import io
        from PIL import Image
        Image.open(io.BytesIO(image_bytes)).verify()
    except Exception:
        return None

    captcha_text = _solve(image_bytes).strip()
    if not captcha_text:
        return None

    resp = session.get(
        f"{_BASE_URL}/resultado.php",
        params={"objeto": probe, "captcha": captcha_text, "mqs": "S"},
        headers=_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    erro = data.get("erro") if isinstance(data, dict) else None
    if erro and "captcha" in data.get("mensagem", "").lower():
        return None

    return image_bytes, captcha_text


def save_sample(image_bytes: bytes, label: str):
    (_DATA_DIR / f"{label}_{int(time.time() * 1000)}.png").write_bytes(image_bytes)


def count_samples() -> int:
    return len(list(_DATA_DIR.glob("*.png")))


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

_MAX_CAPTCHA_MISSES = 8  # erros seguidos de CAPTCHA → troca sessão


def _worker(worker_id: int, probe: str, target: int, delay: float, state: dict, lock: threading.Lock):
    proxy = _proxy_pool.next()
    session = _new_session(proxy)
    consecutive_misses = 0

    while True:
        with lock:
            if state["total_saved"] >= target:
                return
        try:
            result = collect_one(session, probe)
            _proxy_pool.report_ok(proxy)
            with lock:
                state["total_attempts"] += 1
                if state["total_saved"] >= target:
                    return
                if result:
                    consecutive_misses = 0
                    save_sample(*result)
                    state["total_saved"] += 1
                    state["session_saved"] += 1
                    rate = state["session_saved"] / state["total_attempts"] * 100
                    proxy_info = f" proxy={proxy.split('@')[-1] if proxy and '@' in proxy else proxy}" if proxy else ""
                    print(f"[{state['total_saved']}/{target}] '{result[1]}' salvo "
                          f"({rate:.1f}%) [w{worker_id}{proxy_info}]", flush=True)
                else:
                    consecutive_misses += 1
                    if consecutive_misses >= _MAX_CAPTCHA_MISSES:
                        # Sessão PHP pode ter expirado — reinicia com novo proxy
                        consecutive_misses = 0
                        proxy = _proxy_pool.next()
                        session = _new_session(proxy)
        except Exception as e:
            err = str(e)
            if "429" in err:
                # Coloca o proxy atual em cooldown e pega o próximo disponível
                _proxy_pool.report_429(proxy)
                proxy = _proxy_pool.next()
                session = _new_session(proxy)
                print(f"  429 w{worker_id}: trocando proxy → {proxy.split('@')[-1] if proxy and '@' in proxy else proxy}",
                      file=sys.stderr, flush=True)
            else:
                _proxy_pool.report_fail(proxy)
                proxy = _proxy_pool.next()
                session = _new_session(proxy)

        if delay > 0:
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_collector(probe: str, target: int = 1000, delay: float = 0.0, workers: int = 1):
    state = {"total_attempts": 0, "session_saved": 0, "total_saved": count_samples()}
    lock = threading.Lock()
    threads = [
        threading.Thread(target=_worker, args=(i, probe, target, delay, state, lock), daemon=True)
        for i in range(workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    rate = state["session_saved"] / max(state["total_attempts"], 1) * 100
    print(f"Coleta concluída: {state['total_saved']} amostras ({rate:.1f}% acerto)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", required=True,
                        help="Código de rastreamento para validar o CAPTCHA (ex: AA000000000BR)")
    parser.add_argument("--target", type=int, default=15000)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--proxy-api", default="",
                        help="URL da API de proxies (ex: http://host/api/v1/proxy/all)")
    parser.add_argument("--proxy-key", default="",
                        help="API key do servidor de proxies")
    parser.add_argument("--http-only", action="store_true",
                        help="Usa apenas proxies HTTP/HTTPS, ignora socks4/socks5")
    args = parser.parse_args()

    if args.http_only:
        _ProxyPool._http_only = True

    if args.proxy_api and args.proxy_key:
        _proxy_pool.load_from_api(args.proxy_api, args.proxy_key)

    print(f"Coletando {args.target} amostras | {args.workers} workers | "
          f"proxies={len(_proxy_pool)} | existentes: {count_samples()}")
    run_collector(args.probe, args.target, args.delay, args.workers)
