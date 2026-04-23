# 📦 Correios Rastreamento

> Rastreie encomendas dos Correios com histórico completo de eventos, resolução automática de CAPTCHA via rede neural treinada localmente.

Expõe as mesmas operações como **MCP tools** (para agentes AI) e **REST API** (para integrações diretas), com interface web incluída.

---

## 💡 O que este projeto faz

| | |
|--|--|
| 📦 | Rastreia qualquer objeto pelos Correios pelo código (ex: AA000000000BR) |
| 🚀 | Consulta até 20 objetos em paralelo com um único CAPTCHA |
| 🤖 | Integra com qualquer agente AI via protocolo MCP |
| 📋 | Mantém histórico de rastreamentos no servidor |

O rastreamento é feito via scraping do site oficial dos Correios. A resolução de CAPTCHA é feita por uma **CRNN (Convolutional Recurrent Neural Network)** treinada especificamente para isso, atingindo **99.62% de acurácia** sem depender de nenhum serviço externo.

---

## 🤖 MCP Tools

| Tool | Descrição |
| ---- | --------- |
| `rastrear_objeto` | Rastreia um objeto pelo código (ex: AA000000000BR) |
| `rastrear_multiplos` | Rastreia até 20 objetos de uma vez com um único CAPTCHA |

---

## 🌐 REST API

| Método | Rota | Rate limit | Descrição |
| ------ | ---- | ---------- | --------- |
| `GET`  | `/` | — | Interface web |
| `POST` | `/rastreamento/objeto` | 20/min por IP | Rastreia um objeto |
| `POST` | `/rastreamento/multiplos` | 10/min por IP | Rastreia até 20 objetos em paralelo |
| `GET`  | `/history/` | — | Lista o histórico de rastreamentos |
| `POST` | `/history/save` | — | Salva ou atualiza uma entrada no histórico |
| `DELETE` | `/history/` | — | Limpa todo o histórico |
| `DELETE` | `/history/{codigo}` | — | Remove a entrada de um código específico |
| `GET`  | `/health` | — | Health check — retorna `{"status": "ok"}` |

Documentação interativa: `http://localhost:8000/docs` (disponível apenas em `ENV=development`).

---

## 🏗️ Arquitetura

FastAPI com FastMCP 3.0 montado em `/mcp` (streamable-http). A camada `services/` não tem dependência de framework — a mesma lógica é consumida pelos routers REST e pelo MCP server.

```
app/
├── main.py             # FastAPI — routers + mcp.http_app() em /mcp + rate limiter
├── config.py           # Lê todas as variáveis de ambiente com defaults
├── mcp_server.py       # FastMCP("correios-rastreamento") — 2 tools
├── auth.py             # TokenMiddleware — autenticação via API_TOKEN + controle prod/dev
├── services/
│   └── correios.py     # Scraping: curl_cffi + CAPTCHA solver + JSON parsing
├── routers/
│   ├── rastreamento.py # POST /rastreamento/objeto, /rastreamento/multiplos
│   ├── history.py      # GET/POST/DELETE /history/ — histórico de rastreamentos
│   └── ui.py           # GET / — interface web
└── captcha/
    ├── model.py        # Arquitetura CRNN (CNN + BiLSTM + CTC Loss)
    ├── predictor.py    # Inferência: carrega captcha_model.pt e prediz
    ├── dataset.py      # CaptchaDataset com data augmentation
    ├── train.py        # Loop de treino com early stopping + AMP + registry
    ├── collector.py    # Coleta amostras rotuladas direto dos Correios
    ├── evaluate.py     # Avalia acurácia contra amostras salvas
    └── registry.py     # Versionamento de modelos
```

**Regras de camada:**
- `services/` — zero imports de FastAPI ou FastMCP
- `routers/` e `mcp_server.py` — importam apenas de `services/`
- I/O bloqueante em `services/correios.py` é sempre executado via `run_in_threadpool`

---

## ⚙️ Configuração

Todas as opções são lidas de variáveis de ambiente ou do arquivo `.env` na raiz do projeto.

### Referência completa de variáveis

| Variável | Padrão | Descrição |
| -------- | ------ | --------- |
| `API_TOKEN` | *(vazio — sem auth)* | Token Bearer. Se vazio, todos os endpoints ficam abertos |
| `ENV` | `development` | `development` ou `production` — controla quais rotas ficam abertas sem token |
| `RATE_LIMIT_OBJETO` | `20/minute` | Rate limit de `/rastreamento/objeto` por IP |
| `RATE_LIMIT_MULTIPLOS` | `10/minute` | Rate limit de `/rastreamento/multiplos` por IP |
| `HISTORY_RETENTION_DAYS` | `90` | Dias de retenção do histórico. `0` = sem limite |
| `APP_TIMEZONE` | `America/Sao_Paulo` | Timezone para timestamps do histórico |

### 🔒 Rotas abertas por ambiente

| Rota | `development` | `production` |
| ---- | :-----------: | :----------: |
| `/` | ✅ aberta | ✅ aberta |
| `/health` | ✅ aberta | 🔒 token |
| `/docs` | ✅ aberta | 🔒 token |
| `/redoc` | ✅ aberta | 🔒 token |
| `/openapi.json` | ✅ aberta | 🔒 token |
| `/mcp` | 🔒 token | 🔒 token |
| demais | 🔒 token | 🔒 token |

> Se `API_TOKEN` estiver vazio, o middleware ignora autenticação em qualquer ambiente.

---

## 🔐 Autenticação

Com `API_TOKEN` configurado, todas as requisições protegidas precisam enviar:

```
Authorization: Bearer meu-token-secreto
```

**REST:**

```bash
curl -X POST http://localhost:8000/rastreamento/objeto \
  -H "Authorization: Bearer meu-token-secreto" \
  -H "Content-Type: application/json" \
  -d '{"codigo": "AA000000000BR"}'
```

**Claude Desktop / Claude Code (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "correios-rastreamento": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp", "--allow-http"],
      "env": {
        "MCP_REMOTE_HEADER_AUTHORIZATION": "Bearer meu-token-secreto"
      }
    }
  }
}
```

A interface web (`/`) exibe um **gate de autenticação** quando `API_TOKEN` está definido — o token é validado contra o servidor e salvo no navegador.

---

## 🚀 Instalação

### Docker (recomendado)

```bash
git clone https://github.com/opastorello/correios-rastreamento.git
cd correios-rastreamento
cp .env.example .env   # edite se quiser definir API_TOKEN
docker compose up --build -d
```

### Local

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Após iniciar:
- Interface web: `http://localhost:8000/`
- REST docs: `http://localhost:8000/docs` *(apenas em `ENV=development`)*
- MCP endpoint: `http://localhost:8000/mcp`

---

## 📋 Exemplos de uso

### Rastrear um objeto

```bash
curl -X POST http://localhost:8000/rastreamento/objeto \
  -H "Content-Type: application/json" \
  -d '{"codigo": "AA000000000BR"}'
```

```json
{
  "codObjeto": "AA000000000BR",
  "tipoPostal": { "descricao": "SEDEX" },
  "situacao": "E",
  "dtPrevista": "01/01/2026",
  "eventos": [
    {
      "descricaoWeb": "ENTREGUE",
      "dtHrCriado": { "date": "2026-01-01 10:00:00.000000" },
      "unidade": { "endereco": { "cidade": "SAO PAULO", "uf": "SP" } }
    }
  ]
}
```

### Rastrear múltiplos objetos

```bash
curl -X POST http://localhost:8000/rastreamento/multiplos \
  -H "Content-Type: application/json" \
  -d '{"codigos": ["AA000000000BR", "AA000000001BR"]}'
```

---

## 🧠 Modelo de CAPTCHA

### Arquitetura CRNN

```
Input (1×80×215 grayscale)
    → Conv2D ×4 + BatchNorm + ReLU + MaxPool   (extração de features visuais)
    → BiLSTM ×2 (128 hidden, bidirectional)    (modelagem de sequência)
    → Linear → CTC Loss                         (decode sem segmentação)
Output: string [0-9a-z] (CHARSET: 36 chars)
```

### Histórico de treino

| Rodada | Amostras | Rotulador | val_acc |
| ------ | -------- | --------- | :-----: |
| 1 | 55.033 | ddddocr (bootstrap) | 99.57% |
| 2 | 55.000 | Modelo R1 (83.6% acerto) | **99.61%** |
| 3 (fine-tuning) | 20.000 | Modelo R2 (~99%) | 99.63% |
| 4 (fine-tuning) | 100.000 | Modelo R3 (~99%) | **99.62%** |

Resultado v6 sobre 100k amostras: **99.97% por sequência** | **99.99% por caractere**

Erros residuais são confusões visuais: `n↔h`, `e↔c`, `r↔p`, `v↔y`.

### Fluxo de scraping

**Objeto único:**
1. GET `index.php` — session cookie
2. GET `securimage_show.php` — imagem CAPTCHA
3. Resolve com CRNN local (99.62% acurácia)
4. GET `resultado.php?objeto={code}&captcha={text}&mqs=S` — JSON com eventos
5. Retry até 4× em caso de CAPTCHA inválido

**Múltiplos objetos (até 20):**
- Mesmos passos 1–3, mas usa `rastroMulti.php?objeto={cod1cod2...}&captcha={text}`
- **1 CAPTCHA para até 20 objetos** (códigos concatenados)

---

## Treinar o modelo

**1. Coletar amostras**

```bash
python -m app.captcha.collector --probe AA000000000BR --target 20000 --workers 8
```

**2. Treinar do zero**

```bash
python -m app.captcha.train --epochs 80 --batch 128 --lr 1e-3
```

**3. Fine-tuning a partir de checkpoint**

```bash
python -m app.captcha.train --epochs 60 --batch 128 --lr 1e-4 --checkpoint app/captcha/captcha_model.pt
```

O melhor modelo (menor `val_loss`) é salvo em `app/captcha/captcha_model.pt`. Para consultar o histórico de versões:

```bash
python -m app.captcha.registry
```

---

## 📦 Dependências principais

| Pacote | Uso |
| ------ | --- |
| [FastMCP](https://github.com/jlowin/fastmcp) | Framework MCP server |
| [FastAPI](https://github.com/fastapi/fastapi) | REST API |
| [slowapi](https://github.com/laurentS/slowapi) | Rate limiting por IP |
| [curl-cffi](https://github.com/yifeikong/curl-cffi) | HTTP com impersonação TLS Chrome |
| [PyTorch](https://github.com/pytorch/pytorch) | Rede neural CRNN para CAPTCHA |
| [torchvision](https://github.com/pytorch/vision) | Transforms e augmentation de imagem |
| [Pillow](https://github.com/python-pillow/Pillow) | Processamento de imagem |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Carregamento de variáveis do `.env` |

---

## 📄 Licença

[MIT](LICENSE) © 2026 Nícolas Pastorello
