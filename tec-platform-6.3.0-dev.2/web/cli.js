// Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
// Author & Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  const app = document.getElementById('cli-app');
  if (!app || !app.dataset.url) return;
  const state = document.getElementById('cli-state');
  const lista = document.getElementById('sessions');
  const seen = new Set(Array.from(document.querySelectorAll('#sessions h3'), n => n.textContent));
  let ws = null, term = null, refresh = null;
  let ses_rea = '', con_act = false;
  // A dashboard link selects a case; the gateway still checks ownership and consent.
  const cas_id = new URLSearchParams(window.location?.search || '').get('session') || '';
  if (/^[a-f0-9]{32}$/.test(cas_id)) ses_rea = cas_id;
  let firma_lista = '';
  const btn_pegar = document.getElementById('terminal-paste');
  async function request(action, id = '') {
    const body = new URLSearchParams({action, id, node: app.dataset.node, csrf: app.dataset.csrf});
    const res = await fetch('cli.php', {method: 'POST', body, credentials: 'same-origin', cache: 'no-store'});
    const dat = await res.json();
    if (!res.ok) throw new Error(dat.error || 'Pasarela no disponible');
    return dat;
  }
  document.getElementById('notify-enable')?.addEventListener('click', () => {
    if ('Notification' in window) Notification.requestPermission();
  });
  btn_pegar?.addEventListener('click', async () => {
    if (!term || !ws || ws.readyState !== WebSocket.OPEN) return;
    try {
      if (!navigator.clipboard?.readText) throw new Error('El navegador no permite leer el portapapeles aquí.');
      let txt_port = await navigator.clipboard.readText();
      if (!txt_port) throw new Error('El portapapeles está vacío.');
      term.paste(txt_port);
      txt_port = '';
      term.focus();
      state.textContent = 'Texto pegado en la terminal; la entrada puede permanecer oculta.';
    } catch (err) {
      state.textContent = err instanceof Error ? err.message : 'No se pudo leer el portapapeles.';
    }
  });
  async function poll() {
    try {
      const dat = await request('status');
      const fresh = dat.sessions.filter(s => s.state === 'pending' && !seen.has(s.code));
      for (const ses of fresh) {
        seen.add(ses.code);
        if ('Notification' in window && Notification.permission === 'granted')
          new Notification('Nueva asistencia solicitada', {body: ses.code});
      }
      muestra_sesiones(dat.sessions);
      state.textContent = `${dat.sessions.length} solicitudes · ${dat.node}` + (fresh.length ? ' · Nueva solicitud' : ' · Conectado');
      if (ses_rea) {
        const ses = dat.sessions.find(s => s.id === ses_rea);
        if (!ses) ses_rea = '';
        else if (ses.state === 'ready' && !con_act && (!ws || ws.readyState >= 2)) {
          abre_terminal({dataset: {session: ses.id}});
        } else if (['reconnecting', 'awaiting_resume'].includes(ses.state)) {
          state.textContent = 'Reconnecting the authorized case after restart';
        }
      }
    } catch (err) { state.textContent = err.message; }
  }
  function muestra_sesiones(sesiones) {
    const firma = JSON.stringify(sesiones.map(s => [s.id, s.code, s.state]));
    if (firma === firma_lista) return;
    firma_lista = firma;
    const titulo = document.createElement('h2');
    titulo.textContent = 'Solicitudes';
    const filas = [titulo];
    const estados = {pending: 'Pendiente de técnico', awaiting_client: 'Esperando autorización del cliente',
      ready: 'Cliente autorizado · terminal disponible', active: 'Asistencia en curso',
      reconnecting: 'Restarting / reconnecting', awaiting_resume: 'Restoring authorized client'};
    for (const ses of sesiones) {
      const fila = document.createElement('article');
      const codigo = document.createElement('h3');
      codigo.textContent = ses.code;
      const estado = document.createElement('p');
      estado.textContent = estados[ses.state] || ses.state;
      const frm = document.createElement('form');
      frm.method = 'post';
      frm.action = 'cli.php';
      for (const [name, value] of Object.entries({csrf: app.dataset.csrf, node: app.dataset.node,
        id: ses.id, action: ses.state === 'pending' ? 'claim' : 'close'})) {
        const campo = document.createElement('input');
        campo.type = 'hidden'; campo.name = name; campo.value = value;
        frm.append(campo);
      }
      const enviar = document.createElement('button');
      enviar.textContent = ses.state === 'pending' ? 'Aceptar solicitud' : 'Cerrar asistencia';
      frm.append(enviar);
      fila.append(codigo, estado, frm);
      if (ses.state === 'ready') {
        const abrir = document.createElement('button');
        abrir.type = 'button'; abrir.className = 'terminal-open'; abrir.dataset.session = ses.id;
        abrir.textContent = 'Abrir terminal'; fila.append(abrir);
      }
      filas.push(fila);
    }
    // Refresh only the request list; an open terminal and its transport stay attached.
    lista.replaceChildren(...filas);
  }
  lista.addEventListener('click', ev => {
    const btn = ev.target.closest('.terminal-open');
    if (btn) abre_terminal(btn);
  });
  async function abre_terminal(btn) {
    if (con_act || ws && ws.readyState < 2) return;
    con_act = true;
    try {
      if (!window.Terminal) throw new Error('Falta vendor/xterm.js; instalar dependencias de la terminal.');
      const ses = btn.dataset.session;
      ses_rea = ses;
      const dat = await request('ticket', ses);
      term?.dispose();
      term = new Terminal({cols: 100, rows: 30, cursorBlink: true, convertEol: false,
        theme: {background: '#000000', foreground: '#64ff85'}});
      if (btn_pegar) btn_pegar.disabled = true;
      term.open(document.getElementById('terminal'));
      ws = new WebSocket(app.dataset.url.replace('https://', 'wss://') + '/terminal/' + ses);
      const trn_act = ws, trm_act = term;
      ws.binaryType = 'arraybuffer';
      ws.onopen = () => trn_act.send(JSON.stringify({ticket: dat.ticket}));
      ws.onmessage = ev => {
        if (ws !== trn_act) return;
        // xterm maintains its UTF-8 decoder across binary frames, including split accents.
        if (ev.data instanceof ArrayBuffer) {
          const length = ev.data.byteLength;
          trm_act.write(new Uint8Array(ev.data), () => {
            if (trn_act.readyState === 1) trn_act.send(JSON.stringify({type: 'ack', bytes: length}));
          });
        }
        else if (JSON.parse(ev.data).type === 'ready') {
          state.textContent = 'Terminal autorizada';
          if (btn_pegar) btn_pegar.disabled = false;
          term.focus();
        }
      };
      term.onData(txt => {if (trn_act.readyState === 1) trn_act.send(new TextEncoder().encode(txt));});
      term.onBinary(txt => {if (trn_act.readyState === 1) trn_act.send(Uint8Array.from(txt, c => c.charCodeAt(0)));});
      term.onResize(({cols, rows}) => {if (trn_act.readyState === 1) trn_act.send(JSON.stringify({type: 'resize', cols, rows}));});
      ws.onclose = () => {
        if (ws !== trn_act) return;
        clearInterval(refresh);
        if (btn_pegar) btn_pegar.disabled = true;
        state.textContent = 'Connection ended; checking the authorized case';
      };
      ws.onerror = () => {if (ws === trn_act) state.textContent = 'Conexión al cli fallida';};
      refresh = setInterval(async () => {
        if (ws !== trn_act || trn_act.readyState !== 1) return;
        try {
          const next = await request('ticket', ses);
          if (ws === trn_act && trn_act.readyState === 1) trn_act.send(JSON.stringify({type: 'auth', ticket: next.ticket}));
        } catch (err) {
          if (ws === trn_act) {trn_act.close(); state.textContent = err.message;}
        }
      }, 40000);
    } catch (err) {state.textContent = err.message;}
    finally {con_act = false;}
  }
  window.addEventListener('pagehide', () => ws?.close());
  setInterval(poll, 5000); poll();
})();
