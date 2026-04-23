import os

from dotenv import load_dotenv

load_dotenv()

API_TOKEN: str = os.getenv("API_TOKEN", "")
ENV: str = os.getenv("ENV", "development")

RATE_LIMIT_OBJETO: str = os.getenv("RATE_LIMIT_OBJETO", "20/minute")
RATE_LIMIT_MULTIPLOS: str = os.getenv("RATE_LIMIT_MULTIPLOS", "10/minute")

HISTORY_RETENTION_DAYS: int = int(os.getenv("HISTORY_RETENTION_DAYS", "90"))
APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
