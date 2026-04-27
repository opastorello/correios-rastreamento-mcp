from prometheus_client import Counter, Histogram, Gauge

# ── Correios ───────────────────────────────────────────────────────────────────

correios_queries_total = Counter(
    "correios_queries_total",
    "Consultas ao Correios por tipo e resultado",
    ["type", "result"],  # type: single|batch  result: success|not_found|captcha_failed|error
)

correios_captcha_attempts_total = Counter(
    "correios_captcha_attempts_total",
    "Tentativas de resolução de CAPTCHA (cada retry = 1)",
)

correios_captcha_result_total = Counter(
    "correios_captcha_result_total",
    "Resultado de cada tentativa de CAPTCHA",
    ["result"],  # success | wrong | error
)

correios_captcha_duration_seconds = Histogram(
    "correios_captcha_duration_seconds",
    "Tempo para baixar e resolver o CAPTCHA",
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0],
)

correios_query_duration_seconds = Histogram(
    "correios_query_duration_seconds",
    "Tempo total de uma consulta ao Correios (inclui todas as tentativas de CAPTCHA)",
    buckets=[1, 2, 5, 10, 20, 30, 60, 120],
)

correios_captcha_retries_per_query = Histogram(
    "correios_captcha_retries_per_query",
    "Número de tentativas de CAPTCHA necessárias por consulta",
    buckets=[1, 2, 3, 4, 5],
)

correios_concurrent_queries = Gauge(
    "correios_concurrent_queries",
    "Consultas em execução agora (inclui as aguardando semáforo)",
)

correios_http_errors_total = Counter(
    "correios_http_errors_total",
    "Erros HTTP ao se comunicar com o Correios",
    ["type"],  # timeout | connection | http_status
)

correios_batch_size = Histogram(
    "correios_batch_size",
    "Quantidade de objetos por chamada ao /rastreamento/multiplos",
    buckets=[1, 2, 5, 10, 15, 20],
)

# ── History ───────────────────────────────────────────────────────────────────

history_entries_current = Gauge(
    "history_entries_current",
    "Número atual de entradas no histórico server-side",
)

history_saves_total = Counter(
    "history_saves_total",
    "Salvamentos no histórico",
    ["action"],  # new | update
)
