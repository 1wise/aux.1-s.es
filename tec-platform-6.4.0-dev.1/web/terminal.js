// Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
// Author and Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  const app = document.getElementById('terminal-app');
  if (!app?.dataset.url || !/^[a-f0-9]{32}$/.test(app.dataset.session)) return;
  const state = document.getElementById('terminal-state');
  const ses_rea = app.dataset.session;
  const lst_trm = new Map();
  let ws = null, con_act = false, fin_app = false, sync_act = false, tms_ren = null, idx_act = 1;
  if (!window.Terminal) {state.textContent = 'Terminal resources are missing. Install the complete TEC package.'; return;}

  async function request(action) {
    const body = new URLSearchParams({action, id: ses_rea, node: app.dataset.node, csrf: app.dataset.csrf});
    const res = await fetch('cli.php', {method: 'POST', body, credentials: 'same-origin', cache: 'no-store'});
    const dat = await res.json();
    if (!res.ok) throw new Error(dat.error || 'Verify the second factor on the requests page.');
    return dat;
  }
  function controles(trm_act, hab) {
    trm_act.hab = hab;
    trm_act.pegar.disabled = trm_act.interrumpir.disabled = !hab;
  }
  function envia(idx_trm, dat_trm) {
    const trm_act = lst_trm.get(idx_trm);
    if (!trm_act?.hab || ws?.readyState !== WebSocket.OPEN) return;
    // Bound frames even when a clipboard paste contains many lines.
    for (let pos = 0; pos < dat_trm.length; pos += 32768) {
      const dat_par = dat_trm.subarray(pos, pos + 32768);
      const dat_frm = new Uint8Array(dat_par.length + 1); dat_frm[0] = idx_trm; dat_frm.set(dat_par, 1);
      ws.send(dat_frm);
    }
  }
  function ajusta(trm_act) {
    if (!trm_act.grid.clientWidth || trm_act.panel.hidden) return;
    const ctx = document.createElement('canvas').getContext('2d');
    if (!ctx) return;
    ctx.font = '14px monospace';
    const cols = Math.max(20, Math.min(300, Math.floor((trm_act.grid.clientWidth - 20) / ctx.measureText('W').width)));
    const rows = Math.max(5, Math.min(150, Math.floor(trm_act.grid.clientHeight / 18)));
    if (trm_act.term.cols !== cols || trm_act.term.rows !== rows) trm_act.term.resize(cols, rows);
  }
  function selecciona(idx_trm, foco = true) {
    idx_act = idx_trm;
    for (const [idx, trm_act] of lst_trm) {
      const activo = idx === idx_trm;
      trm_act.panel.hidden = !activo; trm_act.tab.setAttribute('aria-selected', String(activo));
      trm_act.tab.tabIndex = activo ? 0 : -1;
    }
    const trm_act = lst_trm.get(idx_trm); ajusta(trm_act);
    if (foco) trm_act.term.focus();
  }
  for (const idx_trm of [1, 2]) {
    const trm_act = {tab: document.getElementById('terminal-tab-' + idx_trm),
      panel: document.getElementById('terminal-panel-' + idx_trm),
      grid: document.getElementById('terminal-' + idx_trm),
      estado: document.getElementById('terminal-status-' + idx_trm),
      pegar: document.getElementById('terminal-paste-' + idx_trm),
      interrumpir: document.getElementById('terminal-interrupt-' + idx_trm), hab: false,
      term: new Terminal({cols: 100, rows: 30, cursorBlink: true, fontSize: 14, fontFamily: 'monospace',
        lineHeight: 18 / 14, theme: {background: '#000000', foreground: '#7bffa0'}})};
    lst_trm.set(idx_trm, trm_act); trm_act.term.open(trm_act.grid); controles(trm_act, false);
    trm_act.term.onData(txt => envia(idx_trm, new TextEncoder().encode(txt)));
    trm_act.term.onBinary(txt => envia(idx_trm, Uint8Array.from(txt, c => c.charCodeAt(0))));
    trm_act.term.onResize(({cols, rows}) => {
      if (trm_act.hab && ws?.readyState === WebSocket.OPEN)
        ws.send(JSON.stringify({type: 'resize', term: idx_trm, cols, rows}));
    });
    trm_act.tab.addEventListener('click', () => selecciona(idx_trm));
    trm_act.tab.addEventListener('keydown', ev => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(ev.key)) return;
      ev.preventDefault(); selecciona(ev.key === 'Home' ? 1 : ev.key === 'End' ? 2 : 3 - idx_act, false);
      lst_trm.get(idx_act).tab.focus();
    });
    trm_act.pegar.addEventListener('click', async () => {
      const trn_act = ws;
      if (!trm_act.hab || trn_act?.readyState !== WebSocket.OPEN) return;
      try {
        if (!navigator.clipboard?.readText) throw new Error('Use the terminal paste shortcut; clipboard access is unavailable.');
        let txt_port = await navigator.clipboard.readText();
        // A clipboard permission prompt can outlive the connection that requested it.
        if (ws !== trn_act || !trm_act.hab || trn_act.readyState !== WebSocket.OPEN) return;
        if (!txt_port) throw new Error('The clipboard is empty.');
        trm_act.term.paste(txt_port); txt_port = ''; trm_act.term.focus();
        trm_act.estado.textContent = 'Clipboard text pasted';
      } catch (err) {trm_act.estado.textContent = err.message;}
    });
    trm_act.interrumpir.addEventListener('click', () => {
      envia(idx_trm, new Uint8Array([3])); trm_act.term.focus();
    });
    if (window.ResizeObserver) new ResizeObserver(() => ajusta(trm_act)).observe(trm_act.grid);
  }
  selecciona(1, false);
  function desconecta(trn_act) {
    if (ws !== trn_act) return;
    clearInterval(tms_ren); tms_ren = null;
    for (const trm_act of lst_trm.values()) {controles(trm_act, false); trm_act.estado.textContent = 'Disconnected';}
  }
  async function abre_terminal() {
    if (fin_app || con_act || ws && ws.readyState < 2) return;
    con_act = true;
    try {
      const dat = await request('ticket');
      if (fin_app) return;
      const trn_act = new WebSocket(app.dataset.url.replace('https://', 'wss://') + '/terminal/' + ses_rea + '?v=2');
      ws = trn_act; trn_act.binaryType = 'arraybuffer';
      trn_act.onopen = () => trn_act.send(JSON.stringify({ticket: dat.ticket}));
      trn_act.onmessage = ev => {
        if (ws !== trn_act || fin_app) return;
        if (ev.data instanceof ArrayBuffer) {
          const dat_frm = new Uint8Array(ev.data); const trm_act = lst_trm.get(dat_frm[0]);
          if (!trm_act || dat_frm.length < 2) {trn_act.close(1008); return;}
          trm_act.term.write(dat_frm.subarray(1), () => {
            if (ws === trn_act && trn_act.readyState === WebSocket.OPEN)
              trn_act.send(JSON.stringify({type: 'ack', bytes: dat_frm.length}));
          });
          return;
        }
        try {
          const dat = JSON.parse(ev.data);
          if (dat.type === 'ready' && dat.term_cnt === 2) {
            for (const [idx_trm, trm_act] of lst_trm) {
              controles(trm_act, true); trm_act.estado.textContent = 'Connected';
              trn_act.send(JSON.stringify({type: 'resize', term: idx_trm, cols: trm_act.term.cols, rows: trm_act.term.rows}));
            }
            state.textContent = 'Two terminals connected'; selecciona(idx_act);
          } else if (dat.type === 'exit' && lst_trm.has(dat.term)) {
            const trm_act = lst_trm.get(dat.term); controles(trm_act, false); trm_act.estado.textContent = 'Shell ended';
          } else {state.textContent = 'The 6.4 update is required on the gateway and Live client for two terminals.'; trn_act.close(1008);}
        } catch {state.textContent = 'Invalid terminal response'; trn_act.close(1008);}
      };
      trn_act.onclose = () => {
        if (ws !== trn_act) return;
        desconecta(trn_act);
        if (!fin_app) state.textContent = 'Connection ended. Checking the authorized case…';
      };
      trn_act.onerror = () => {if (ws === trn_act) state.textContent = 'Gateway connection failed';};
      clearInterval(tms_ren);
      tms_ren = setInterval(async () => {
        if (ws !== trn_act || trn_act.readyState !== WebSocket.OPEN) return;
        try {
          const dat = await request('ticket');
          if (ws === trn_act && trn_act.readyState === WebSocket.OPEN)
            trn_act.send(JSON.stringify({type: 'auth', ticket: dat.ticket}));
        } catch (err) {if (ws === trn_act) {desconecta(trn_act); trn_act.close(); state.textContent = err.message;}}
      }, 40000);
    } catch (err) {state.textContent = err.message;}
    finally {con_act = false;}
  }
  async function poll() {
    if (fin_app || sync_act) return;
    sync_act = true;
    try {
      const dat = await request('status'); if (fin_app) return;
      const ses = dat.sessions.find(s => s.id === ses_rea);
      if (!ses) {fin_app = true; desconecta(ws); ws?.close(); state.textContent = 'The case is closed or unavailable.'; return;}
      if (ses.state === 'ready' && (!ws || ws.readyState >= 2)) {
        if (ses.term_cnt !== 2) {state.textContent = 'The 6.4 update is required on the gateway and Live client for two terminals.'; return;}
        await abre_terminal();
      } else if (['reconnecting', 'awaiting_resume'].includes(ses.state)) {
        state.textContent = 'Waiting for the authorized client to reconnect…';
      } else if (ses.state === 'awaiting_client') state.textContent = 'Waiting for client consent…';
      else if (ses.state === 'active' && !ws) state.textContent = 'A terminal workspace is already open for this case.';
    } catch (err) {state.textContent = err.message;}
    finally {sync_act = false;}
  }
  const int_est = setInterval(poll, 5000); poll();
  window.addEventListener('pagehide', () => {
    fin_app = true; clearInterval(int_est); desconecta(ws); ws?.close();
    for (const trm_act of lst_trm.values()) trm_act.term.dispose();
  });
})();
