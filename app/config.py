import os

from dotenv import load_dotenv

load_dotenv()


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default

def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default

def _str(key: str, default: str) -> str:
    return os.getenv(key, default).strip()


# ── Ambiente ────────────────────────────────────────────────
ENV                     = _str("ENV", "development")
IS_PRODUCTION           = ENV == "production"

# ── Auth ────────────────────────────────────────────────────
API_TOKEN               = _str("API_TOKEN", "")

# ── Correios scraping ────────────────────────────────────────
HTTP_TIMEOUT            = _float("HTTP_TIMEOUT", 30.0)
CAPTCHA_TIMEOUT         = _float("CAPTCHA_TIMEOUT", 15.0)
MAX_RETRIES             = _int("MAX_RETRIES", 4)
MAX_CONCURRENT          = _int("MAX_CONCURRENT", 10)

# ── Rate limits (formato slowapi: "N/minute" ou "N/second") ──
RATE_LIMIT_OBJETO       = _str("RATE_LIMIT_OBJETO", "20/minute")
RATE_LIMIT_MULTIPLOS    = _str("RATE_LIMIT_MULTIPLOS", "10/minute")

# ── Captcha model ────────────────────────────────────────────
CAPTCHA_MODEL_PATH      = _str("CAPTCHA_MODEL_PATH", "")   # vazio = path padrão relativo

# ── Histórico ────────────────────────────────────────────────
HISTORY_RETENTION_DAYS  = _int("HISTORY_RETENTION_DAYS", 90)
APP_TIMEZONE            = _str("APP_TIMEZONE", "America/Sao_Paulo")
