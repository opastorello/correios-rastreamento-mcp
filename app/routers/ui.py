from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.auth import _TOKEN

router = APIRouter(include_in_schema=False)

_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Correios Rastreamento</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📦</text></svg>">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg: #0d1117;
      --surface: #161b22;
      --surface2: #1c2128;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #7d8590;
      --accent: #1f6feb;
      --accent-h: #388bfd;
      --green: #3fb950;
      --r: 10px;
    }

    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 20px 80px;
    }

    .logo { font-size: 28px; margin-bottom: 6px; }

    h1 {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -.3px;
      margin-bottom: 6px;
      text-align: center;
    }

    .sub { font-size: 13px; color: var(--muted); margin-bottom: 28px; text-align: center; }

    #main-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
    }

    .wrap { width: 100%; max-width: 520px; }

    .tabs {
      display: flex;
      gap: 4px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 4px;
      margin-bottom: 14px;
    }

    .tab {
      flex: 1;
      text-align: center;
      padding: 8px;
      font-size: 13px;
      font-weight: 600;
      color: var(--muted);
      border-radius: 7px;
      cursor: pointer;
      transition: background .15s, color .15s;
      user-select: none;
    }

    .tab.active { background: var(--surface2); color: var(--text); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 26px 26px 22px;
    }

    .field + .field { margin-top: 15px; }

    label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .07em;
      color: var(--muted);
      margin-bottom: 7px;
    }

    input {
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 11px 14px;
      color: var(--text);
      font-size: 15px;
      font-family: inherit;
      outline: none;
      transition: border-color .15s, box-shadow .15s;
      text-transform: uppercase;
    }

    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(31,111,235,.15);
    }

    input::placeholder { color: var(--muted); text-transform: none; }

    button {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 7px;
      padding: 12px;
      font-size: 14px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      margin-top: 20px;
      transition: background .15s;
    }

    button:hover:not(:disabled) { background: var(--accent-h); }
    button:disabled { opacity: .5; cursor: not-allowed; }

    /* ── result ── */
    .result-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      overflow: hidden;
      margin-top: 14px;
    }

    .result-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 15px 18px 12px;
      border-bottom: 1px solid var(--border);
      gap: 12px;
    }

    .result-code { font-weight: 700; font-size: 16px; font-variant-numeric: tabular-nums; letter-spacing: .03em; }
    .result-type { font-size: 13px; color: var(--muted); }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      white-space: nowrap;
    }

    .badge-delivered { background: rgba(63,185,80,.15); color: var(--green); }
    .badge-transit   { background: rgba(31,111,235,.15); color: var(--accent-h); }

    .result-meta {
      padding: 10px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
    }

    .meta-item { font-size: 12px; color: var(--muted); }
    .meta-item strong { color: var(--text); font-weight: 500; }

    /* ── timeline ── */
    .timeline { padding: 6px 18px 14px; }

    .tl-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .07em;
      color: var(--muted);
      margin: 12px 0 10px;
    }

    .event {
      display: flex;
      gap: 14px;
      padding: 8px 0;
      border-bottom: 1px solid var(--border);
    }

    .event:last-child { border-bottom: none; }

    .event-dot {
      flex-shrink: 0;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--border);
      margin-top: 5px;
    }

    .event-dot.first { background: var(--green); box-shadow: 0 0 0 3px rgba(63,185,80,.2); }
    .event-dot.transit { background: var(--accent); }

    .event-body { flex: 1; min-width: 0; }
    .event-desc { font-size: 13.5px; font-weight: 500; }
    .event-loc { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .event-time { font-size: 11px; color: var(--muted); white-space: nowrap; margin-top: 1px; font-variant-numeric: tabular-nums; }

    .err-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 14px 18px;
      font-size: 14px;
      color: var(--muted);
      margin-top: 14px;
    }

    /* ── history ── */
    .hist-actions {
      display: flex;
      justify-content: flex-end;
      margin-bottom: 10px;
    }

    .hist-clear {
      background: none;
      border: 1px solid var(--border);
      border-radius: 5px;
      color: var(--muted);
      font-size: 11px;
      font-family: inherit;
      padding: 3px 8px;
      cursor: pointer;
      margin-top: 0;
      width: auto;
      transition: color .15s, border-color .15s;
    }

    .hist-clear:hover { color: var(--text); border-color: var(--muted); }

    .hist-del {
      background: none;
      border: none;
      color: var(--muted);
      font-size: 18px;
      line-height: 1;
      cursor: pointer;
      padding: 4px 7px;
      margin: 0;
      width: auto;
      margin-top: 0;
      border-radius: 5px;
      flex-shrink: 0;
      transition: color .15s, background .15s;
    }

    .hist-del:hover { color: var(--text); background: var(--surface2); }

    .hist-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 9px 10px;
      border-radius: 7px;
      cursor: pointer;
      transition: background .12s;
      gap: 12px;
    }

    .hist-item:hover { background: var(--surface2); }

    .hist-code {
      font-size: 13.5px;
      font-weight: 600;
      letter-spacing: .03em;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }

    .hist-status {
      font-size: 12px;
      margin-top: 2px;
    }

    .hist-time { font-size: 11px; color: var(--muted); white-space: nowrap; }

    .hist-empty {
      text-align: center;
      color: var(--muted);
      font-size: 13px;
      padding: 32px 0;
    }

    /* ── gate ── */
    .spin {
      width: 15px; height: 15px;
      border: 2px solid rgba(255,255,255,.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: rot .65s linear infinite;
      flex-shrink: 0;
    }

    @keyframes rot { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <div id="gate" style="display:none;width:100%;max-width:400px;text-align:center">
    <div class="logo">🔒</div>
    <h1>Acesso restrito</h1>
    <p class="sub">Informe o API Token para continuar</p>
    <div class="card" style="margin-top:20px">
      <div class="field">
        <label>API Token</label>
        <input id="gate-token" type="password" placeholder="Token de acesso" autocomplete="off" style="text-transform:none" />
      </div>
      <button id="btn-gate" onclick="gateLogin()" style="margin-top:14px">Entrar</button>
      <div id="gate-msg" style="display:none;margin-top:10px;font-size:13px"></div>
    </div>
  </div>

  <div id="main-content">
    <div class="logo">📦</div>
    <h1>Rastreamento Correios</h1>
    <p class="sub">Acompanhe o status de entrega dos seus objetos</p>

    <div class="wrap">
      <div class="tabs">
        <div class="tab active" id="tab-rastrear" onclick="switchTab('rastrear')">Rastrear</div>
        <div class="tab"        id="tab-historico" onclick="switchTab('historico')">Histórico</div>
      </div>

      <!-- aba rastrear -->
      <div class="tab-panel active" id="panel-rastrear">
        <div class="card">
          <div class="field">
            <label>Código de rastreamento</label>
            <input id="codigo" type="text" placeholder="AA000000000BR"
                   spellcheck="false" autocomplete="off" maxlength="13" />
          </div>
          <button id="btn" onclick="rastrear()">Rastrear</button>
        </div>
        <div id="out"></div>
      </div>

      <!-- aba histórico -->
      <div class="tab-panel" id="panel-historico">
        <div class="card">
          <div class="hist-actions">
            <button class="hist-clear" onclick="clearHistory()">Limpar histórico</button>
          </div>
          <div id="hist-list"></div>
        </div>
      </div>
    </div>
  </div>

  <footer style="text-align:center;padding:20px 0 16px;font-size:12px;color:var(--muted);">
    <a href="https://github.com/opastorello/correios-rastreamento" target="_blank" rel="noopener"
       style="color:var(--muted);text-decoration:none;display:inline-flex;align-items:center;gap:6px;">
      <svg height="16" width="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
        0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
        -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
        .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
        -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27
        .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
        .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
        0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
      </svg>
      opastorello/correios-rastreamento
    </a>
  </footer>

  <script>
    const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');

    const $codigo  = document.getElementById('codigo');
    const $btn     = document.getElementById('btn');
    const $out     = document.getElementById('out');

    $codigo.addEventListener('input', function() {
      this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 13);
    });
    $codigo.addEventListener('keydown', e => { if (e.key === 'Enter') rastrear(); });

    const AUTH_REQUIRED = __AUTH_REQUIRED__;
    const getToken = () => localStorage.getItem('api_token') || '';
    const authH = () => { const t = getToken(); return t ? {'Authorization': 'Bearer ' + t} : {}; };
    const post = (path, body) => fetch(path, { method: 'POST', headers: {'Content-Type':'application/json', ...authH()}, body: JSON.stringify(body) });

    /* ── rastrear ── */
    async function rastrear() {
      const codigo = $codigo.value.trim();
      if (!codigo) { $codigo.focus(); return; }

      $btn.disabled = true;
      $btn.innerHTML = '<span class="spin"></span>Rastreando…';
      $out.innerHTML = '';

      const t0 = Date.now();

      try {
        const res  = await post('/rastreamento/objeto', { codigo });
        const data = await res.json();
        const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

        if (!res.ok) {
          $out.innerHTML = `<div class="err-box">⚠️ ${esc(data.detail || 'Erro na consulta')}</div>`;
          return;
        }

        if (data.erro) {
          $out.innerHTML = `<div class="err-box">⚠️ ${esc(data.mensagem || 'Objeto não encontrado.')}</div>`;
          return;
        }

        const entregue = (data.situacao || '').toUpperCase() === 'E';
        const eventos = data.eventos || [];
        const lastEvento = eventos[0] || {};
        const lastStatus = (lastEvento.descricaoWeb || '').toUpperCase();

        const badgeClass = entregue ? 'badge-delivered' : 'badge-transit';
        const badgeIcon  = entregue ? '✓' : '↻';
        const badgeText  = entregue ? 'Entregue' : (lastStatus || 'Em andamento');
        const tipoDesc   = (data.tipoPostal || {}).descricao || '';

        const eventsHtml = eventos.map((ev, i) => {
          const dtRaw = (ev.dtHrCriado || {}).date || '';
          const dtFmt = fmtDatetime(dtRaw);
          const loc = formatLoc(ev.unidade);
          const desc = esc(ev.descricaoWeb || ev.descricaoFrontEnd || '');
          const dotClass = i === 0 ? (entregue ? 'first' : 'transit') : '';
          return `
          <div class="event">
            <div class="event-dot ${dotClass}"></div>
            <div class="event-body">
              <div class="event-desc">${desc}</div>
              ${loc ? `<div class="event-loc">${esc(loc)}</div>` : ''}
              ${dtFmt ? `<div class="event-time">${esc(dtFmt)}</div>` : ''}
            </div>
          </div>`;
        }).join('');

        $out.innerHTML = `
          <div class="result-card">
            <div class="result-head">
              <div>
                <div class="result-code">${esc(data.codObjeto || codigo)}</div>
                ${tipoDesc ? `<div class="result-type">${esc(tipoDesc)}</div>` : ''}
              </div>
              <span class="badge ${badgeClass}">${badgeIcon} ${esc(badgeText)}</span>
            </div>
            ${data.dtPrevista ? `
            <div class="result-meta">
              <div class="meta-item">Previsão de entrega: <strong>${esc(data.dtPrevista)}</strong></div>
              <div class="meta-item">Consultado em <strong>${elapsed}s</strong></div>
            </div>` : `
            <div class="result-meta">
              <div class="meta-item">Consultado em <strong>${elapsed}s</strong></div>
            </div>`}
            ${eventos.length ? `
            <div class="timeline">
              <div class="tl-label">Histórico de eventos (${eventos.length})</div>
              ${eventsHtml}
            </div>` : ''}
          </div>`;

        saveToHistory(data.codObjeto || codigo, lastStatus || null, entregue, parseFloat(elapsed));

      } catch (e) {
        $out.innerHTML = `<div class="err-box">⚠️ ${esc(e.message)}</div>`;
      } finally {
        $btn.disabled = false;
        $btn.textContent = 'Rastrear';
      }
    }

    function fmtDatetime(raw) {
      if (!raw) return '';
      const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
      if (!m) return raw;
      return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`;
    }

    function formatLoc(unidade) {
      if (!unidade) return '';
      const end = unidade.endereco || {};
      const parts = [end.cidade, end.uf].filter(Boolean);
      const loc = parts.join(' — ');
      const tipo = unidade.tipo || '';
      return [tipo, loc].filter(Boolean).join(', ');
    }

    /* ── gate ── */
    function updateVisibility() {
      const locked = AUTH_REQUIRED && !getToken();
      document.getElementById('gate').style.display         = locked ? 'block' : 'none';
      document.getElementById('main-content').style.display = locked ? 'none'  : '';
    }

    async function gateLogin() {
      const tok = document.getElementById('gate-token').value.trim();
      if (!tok) return;
      const btn = document.getElementById('btn-gate');
      const msg = document.getElementById('gate-msg');
      btn.disabled = true;
      btn.textContent = 'Validando…';
      try {
        const res = await fetch('/history/', { headers: { 'Authorization': 'Bearer ' + tok } });
        if (res.status === 401) {
          showGateMsg('✕ Token inválido.'); btn.disabled = false; btn.textContent = 'Entrar'; return;
        }
      } catch {
        showGateMsg('⚠ Erro ao validar.'); btn.disabled = false; btn.textContent = 'Entrar'; return;
      }
      localStorage.setItem('api_token', tok);
      btn.disabled = false; btn.textContent = 'Entrar';
      updateVisibility();
    }

    function showGateMsg(text) {
      const msg = document.getElementById('gate-msg');
      msg.textContent = text; msg.style.display = 'block';
      setTimeout(() => { msg.style.display = 'none'; }, 3000);
    }

    document.getElementById('gate-token').addEventListener('keydown', e => { if (e.key === 'Enter') gateLogin(); });
    updateVisibility();

    /* ── tabs ── */
    function switchTab(name) {
      if (AUTH_REQUIRED && !getToken()) return;
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      document.getElementById('panel-' + name).classList.add('active');
      if (name === 'historico') renderHistory();
    }

    /* ── history ── */
    async function saveToHistory(codigo, status, entregue, duracao_segundos) {
      await fetch('/history/save', {
        method: 'POST',
        headers: {'Content-Type':'application/json', ...authH()},
        body: JSON.stringify({ codigo, status, entregue, duracao_segundos })
      }).catch(() => {});
    }

    async function clearHistory() {
      await fetch('/history/', { method: 'DELETE', headers: {...authH()} }).catch(() => {});
      renderHistory();
    }

    async function deleteHistoryEntry(codigo) {
      await fetch('/history/' + encodeURIComponent(codigo), { method: 'DELETE', headers: {...authH()} }).catch(() => {});
      renderHistory();
    }

    function fmtDt(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      const today = new Date();
      const hm = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      if (d.toDateString() === today.toDateString()) return 'Hoje ' + hm;
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' }) + ' ' + hm;
    }

    async function renderHistory() {
      const $list = document.getElementById('hist-list');
      $list.innerHTML = '<div class="hist-empty">Carregando…</div>';
      try {
        const res  = await fetch('/history/', { headers: {...authH()} });
        const data = await res.json();
        const entries = data.entries || [];
        if (!entries.length) {
          $list.innerHTML = '<div class="hist-empty">Nenhum rastreamento registrado ainda.</div>';
          return;
        }
        $list.innerHTML = entries.map(h => {
          const statusColor = h.entregue ? 'var(--green)' : 'var(--accent-h)';
          const statusText  = h.status || (h.entregue ? 'ENTREGUE' : 'EM ANDAMENTO');
          return `
          <div class="hist-item" onclick="fillFromHistory('${esc(h.codigo)}')">
            <div style="flex:1;min-width:0">
              <div class="hist-code">${esc(h.codigo)}</div>
              <div class="hist-status" style="color:${statusColor}">${esc(statusText)}</div>
              ${h.ultima_duracao_s != null ? `<div style="font-size:11px;color:var(--muted);margin-top:2px">${esc(h.ultima_duracao_s)}s · ${esc(h.consultas)}× consultado</div>` : `<div style="font-size:11px;color:var(--muted);margin-top:2px">${esc(h.consultas)}× consultado</div>`}
            </div>
            <div style="text-align:right;flex-shrink:0">
              <div class="hist-time">${fmtDt(h.ultima_consulta)}</div>
            </div>
            <button class="hist-del" title="Remover entrada"
              onclick="event.stopPropagation(); deleteHistoryEntry('${esc(h.codigo)}')">×</button>
          </div>`;
        }).join('');
      } catch {
        $list.innerHTML = '<div class="hist-empty">Erro ao carregar histórico.</div>';
      }
    }

    function fillFromHistory(codigo) {
      switchTab('rastrear');
      $codigo.value = codigo;
      $out.innerHTML = '';
    }
  </script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def ui():
    auth_required = "true" if _TOKEN else "false"
    return _HTML.replace("__AUTH_REQUIRED__", auth_required)
