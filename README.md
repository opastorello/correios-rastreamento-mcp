# correios-rastreamento-mcp

[![CI](https://github.com/opastorello/correios-rastreamento-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/opastorello/correios-rastreamento-mcp/actions/workflows/ci.yml)
[![Docker](https://github.com/opastorello/correios-rastreamento-mcp/actions/workflows/docker.yml/badge.svg)](https://github.com/opastorello/correios-rastreamento-mcp/actions/workflows/docker.yml)

MCP server para rastreamento de objetos dos Correios, com scraping automático e solver de CAPTCHA próprio (CRNN).

## Stack

- **FastAPI** + **FastMCP 3.0** — REST + MCP transport em `/mcp`
- **curl_cffi** — scraping com impersonação TLS (Chrome)
- **PyTorch CRNN** — solver de CAPTCHA local, sem API externa

## Início rápido

```bash
# Produção (CPU)
pip install -r requirements.txt

# Desenvolvimento — treino + coleta (inclui ddddocr)
pip install -r requirements-dev.txt

# Desenvolvimento com GPU (CUDA 12.4) — recomendado para treino
pip install -r requirements-dev.txt --index-url https://download.pytorch.org/whl/cu124

# Rodar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Docs REST: `http://localhost:8000/docs`
- MCP endpoint: `http://localhost:8000/mcp`

### Docker

```bash
# Imagem pré-compilada (recomendado)
docker pull ghcr.io/opastorello/correios-rastreamento-mcp:latest
docker run -p 8000:8000 ghcr.io/opastorello/correios-rastreamento-mcp:latest

# Com token de autenticação
docker run -p 8000:8000 -e API_TOKEN=seu_token ghcr.io/opastorello/correios-rastreamento-mcp:latest

# Ou compilar localmente
docker build -t correios-rastreamento .
docker run -p 8000:8000 correios-rastreamento
```

## Endpoints REST

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/rastreamento/objeto` | Rastreia um objeto |
| POST | `/rastreamento/multiplos` | Rastreia até 20 objetos (1 CAPTCHA) |
| GET | `/health` | Health check (sempre público) |

## MCP Tools

Endpoint: `http://localhost:8000/mcp`

| Tool | Descrição |
|------|-----------|
| `rastrear_objeto` | Rastreia um objeto pelo código (ex: AA000000000BR) |
| `rastrear_multiplos` | Rastreia até 20 objetos de uma vez |

## Autenticação

Opcional via variável de ambiente `API_TOKEN`. Se definida, exige `Authorization: Bearer <token>` em todas as rotas exceto `/health`.

```env
API_TOKEN=seu_token_aqui
```

| Cenário | REST API | MCP |
|---------|----------|-----|
| Sem `API_TOKEN` configurado | ✅ livre | ✅ livre |
| Com `API_TOKEN` — sem token | ❌ 401 | ❌ 401 |
| Com `API_TOKEN` — token errado | ❌ 401 | ❌ 401 |
| Com `API_TOKEN` — token correto | ✅ 200 | ✅ OK |
| `/health` | ✅ sempre público | — |

## CAPTCHA Solver (CRNN)

Solver local baseado em rede neural (CNN + BiLSTM + CTC Loss), treinado nas imagens reais do site dos Correios.

### Modelo

| Parâmetro | Valor |
|-----------|-------|
| Arquitetura | CNN (4 camadas) + BiLSTM (2 camadas, 128 hidden) + CTC |
| CHARSET | `0-9a-z` (36 chars) |
| Imagem | 215x80px grayscale |
| Modelo | `app/captcha/captcha_model.pt` |

### Histórico de treino

| Rodada | Amostras | val_acc | Rotulador |
|--------|----------|---------|-----------|
| 1 | 55.033 | 99.57% | ddddocr (bootstrap) |
| 2 | 55.000 | **99.61%** | Modelo R1 (83.6% acerto na coleta) |
| 3 (fine-tuning) | 20.000 | 99.63% | Modelo R2 (~99% acerto na coleta) |
| 4 (fine-tuning) | 100.000 | **99.62%** | Modelo R3 (~99% acerto na coleta) |

### Comandos (desenvolvimento)

```bash
# Coletar amostras (com pool de proxies)
.venv\Scripts\python -m app.captcha.collector --probe AA000000000BR --target 20000 --workers 8 \
  --proxy-api http://host/api/v1/proxy/all --proxy-key APIKEY

# Treinar do zero
.venv\Scripts\python -m app.captcha.train --epochs 80 --batch 128 --lr 1e-3

# Fine-tuning a partir de checkpoint
.venv\Scripts\python -m app.captcha.train --epochs 60 --batch 128 --lr 1e-4 --checkpoint app/captcha/captcha_model.pt

# Aguardar coleta terminar e treinar automaticamente
.venv\Scripts\python -m app.captcha.train --wait-for 100000 --epochs 60 --lr 1e-4 --checkpoint app/captcha/captcha_model.pt

# Ver histórico de versões
.venv\Scripts\python -m app.captcha.registry
```

### Pipeline de bootstrapping

```
Rodada 1: ddddocr (~40-50% acurácia labels) → modelo ~98-99%
Rodada 2: modelo R1 (~83-87% acurácia labels) → modelo ~99.5%+
Rodada 3: modelo R2 (~99%+ acurácia labels)   → teto da arquitetura (~99.6%)
```

### Avaliação interna

```bash
# Avalia o modelo contra todas as amostras salvas
.venv\Scripts\python -m app.captcha.evaluate

# Amostra aleatória de 5000 imagens
.venv\Scripts\python -m app.captcha.evaluate --samples 5000
```

Resultado v6 sobre 100k amostras: **99.97% por sequência** | **99.99% por caractere**
(val_acc honesta sobre dados nunca vistos: **99.62%**)

Erros residuais são confusões visuais esperadas: `n↔h`, `e↔c`, `r↔p`, `v↔y`.

## Fluxo de scraping

**Objeto único:**
1. GET `index.php` — session cookie
2. GET `securimage_show.php` — imagem CAPTCHA
3. Resolve CAPTCHA com CRNN local (99.62% acurácia)
4. GET `resultado.php?objeto={code}&captcha={text}&mqs=S` — JSON com eventos
5. Retry até 4x em caso de CAPTCHA inválido

**Múltiplos objetos (até 20):**
- Mesmos passos 1-3, mas usa `rastroMulti.php?objeto={cod1cod2...}&captcha={text}`
- **1 CAPTCHA para até 20 objetos** (códigos concatenados sem separador)

## Estrutura

```
app/
├── main.py              # FastAPI app + lifespan MCP
├── mcp_server.py        # FastMCP server
├── auth.py              # TokenMiddleware (opcional)
├── services/
│   └── correios.py      # Scraping
├── routers/
│   └── rastreamento.py  # Endpoints REST
└── captcha/
    ├── model.py         # Arquitetura CRNN
    ├── predictor.py     # Inferência (produção)
    ├── dataset.py       # Dataset + augmentation (dev)
    ├── train.py         # Loop de treino — suporta --checkpoint e --wait-for (dev)
    ├── evaluate.py      # Avalia acurácia contra amostras salvas (dev)
    ├── collector.py     # Coleta de amostras (dev)
    └── registry.py      # Versionamento de modelos (dev)
```
