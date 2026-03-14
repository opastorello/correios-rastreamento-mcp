# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Instalar dependências de produção
pip install -r requirements.txt

# Instalar dependências de desenvolvimento (treino + coleta de CAPTCHA)
pip install -r requirements-dev.txt

# Run server locally (FastAPI + FastMCP on port 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker
docker build -t correios-rastreamento .
docker run -p 8000:8000 correios-rastreamento
```

Manual testing:
- FastAPI docs: `http://localhost:8000/docs`
- MCP transport: `http://localhost:8000/mcp` (streamable-http)

## Architecture

FastAPI app (`app/main.py`) that includes REST routers **and** mounts a FastMCP 3.0 server at `/mcp`.

```
app/
├── main.py              # FastAPI app — includes routers, mounts mcp.http_app() at /mcp
├── mcp_server.py        # FastMCP("correios-rastreamento") — tools wrapping services
├── auth.py              # TokenMiddleware — optional auth via API_TOKEN env var
├── services/
│   └── correios.py      # Scraping: curl_cffi + CAPTCHA solver + JSON parsing
├── routers/
│   └── rastreamento.py  # POST /rastreamento/objeto, POST /rastreamento/multiplos
└── captcha/
    ├── model.py         # CRNN architecture (CNN + BiLSTM + CTC Loss), CHARSET, IMG_H/W
    ├── dataset.py       # CaptchaDataset — filename format: {label}_{timestamp_ms}.png
    ├── train.py         # Training loop with early stopping + AMP
    ├── predictor.py     # Inference — lazy-loads captcha_model.pt on first call
    ├── collector.py     # Collects labeled samples; supports proxy pool + multithreading
    └── registry.py      # Model versioning — saves to registry.json
```

### Layer rules
- `services/` has **no FastAPI or FastMCP imports** — pure Python
- `routers/` and `mcp_server.py` both import from `services/`
- Blocking I/O in `services/correios.py` is always wrapped with `run_in_threadpool`

### MCP tools
| Tool | Description |
|------|-------------|
| `rastrear_objeto` | Rastreia um objeto pelo código (ex: AA000000000BR) |
| `rastrear_multiplos` | Rastreia até 20 objetos de uma vez |

### REST endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/rastreamento/objeto` | Rastreia um objeto |
| POST | `/rastreamento/multiplos` | Rastreia múltiplos objetos (até 20) |
| GET | `/health` | Health check |

### Correios scraping flow
1. GET `index.php` → obtém session cookie (PHP session)
2. GET `securimage_show.php` → baixa imagem do CAPTCHA (Securimage)
3. Resolve CAPTCHA com **CRNN local** (PyTorch) ou ddddocr como fallback
4. GET `resultado.php?objeto={code}&captcha={text}&mqs=S` → JSON com eventos
5. Retry até 4× em caso de CAPTCHA inválido

### CAPTCHA model
- Arquitetura: CNN (4 camadas conv+bn+relu+pool) → BiLSTM (2 camadas, 128 hidden) → FC → CTC Loss
- CHARSET: `0-9a-z` (36 chars), BLANK = índice 36
- Imagem: 215×80px grayscale
- Amostras ficam em `app/captcha/data/*.png` com nome `{label}_{timestamp_ms}.png`
- Modelo salvo em `app/captcha/captcha_model.pt`; histórico em `app/captcha/registry.json`
- No Windows, `num_workers=0` é forçado no DataLoader (limitação PyTorch+CUDA)

### Collector de amostras

```bash
# Sem proxy
python -m app.captcha.collector --probe AA000000000BR --target 20000 --workers 8

# Com proxy API (todos os tipos)
python -m app.captcha.collector --probe AA000000000BR --target 20000 --workers 50 \
  --proxy-api http://host/api/v1/proxy/all --proxy-key APIKEY

# Apenas proxies HTTP autenticados (mais estável, sem socks públicos)
python -m app.captcha.collector --probe AA000000000BR --target 20000 --workers 50 \
  --proxy-api http://host/api/v1/proxy/all --proxy-key APIKEY --http-only
```

**Proxy pool (`_ProxyPool`):**
- Rotação round-robin thread-safe
- `--http-only`: filtra `socks4`/`socks5`, usa só `http`/`https`
- Cooldown de 60s por proxy após 429 (não conta como falha)
- Blacklist automática: proxy banido após 3 falhas consecutivas de rede
- Auto-reload: quando o pool esvazia, recarrega da API; se API falhar, reseta os bans e restaura backup local
- `PageSize=1000` por chamada — carrega tudo em uma única request

**A API de proxies** deve retornar JSON com `items[]`, cada item com: `host`, `port`, `type` (`http`/`https`/`socks4`/`socks5`), `username`, `password` (opcionais).

**Sweet spot de workers:** `proxies_disponíveis / 60 × tempo_médio_request ≈ 64 workers` com 950 proxies. Acima disso os workers ficam esperando cooldown.

Treino e versionamento:
```bash
python -m app.captcha.train --epochs 80 --batch 128 --lr 1e-3
python -m app.captcha.registry   # lista versões treinadas
```

### Authentication
- `API_TOKEN` env var — opcional. Se definido, exige `Authorization: Bearer <token>`
- Rotas `/health`, `/docs`, `/redoc`, `/openapi.json` são sempre públicas
- Configurar em `.env` (ver `.env.example`)

## Context
- Projeto irmão: `../cpf-validador-mcp` (trt3-mcp) — mesma arquitetura
- CAPTCHA pipeline documentado na skill `/captcha-crnn`
