// Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
// Author and Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  const app = document.getElementById('cli-app');
  if (!app || !app.dataset.url) return;
  const state = document.getElementById('cli-state');
  const lista = document.getElementById('sessions');
  const seen = new Set(Array.from(document.querySelectorAll('#sessions h3'), n => n.textContent));
  let firma_lista = '', con_act = false;
  document.getElementById('notify-enable')?.addEventListener('click', () => {
    if ('Notification' in window) Notification.requestPermission();
  });
  function muestra_sesiones(sesiones) {
    const firma = JSON.stringify(sesiones.map(s => [s.id, s.code, s.state]));
    if (firma === firma_lista) return;
    firma_lista = firma;
    const titulo = document.createElement('h2'); titulo.textContent = 'Requests';
    const filas = [titulo];
    const estados = {pending: 'Waiting for technician', awaiting_client: 'Waiting for client consent',
      ready: 'Client authorized', active: 'Terminal workspace open',
      reconnecting: 'Restarting / reconnecting', awaiting_resume: 'Restoring authorized client'};
    for (const ses of sesiones) {
      const fila = document.createElement('article');
      const codigo = document.createElement('h3'); codigo.textContent = ses.code;
      const estado = document.createElement('p'); estado.textContent = estados[ses.state] || ses.state;
      const frm = document.createElement('form'); frm.method = 'post'; frm.action = 'cli.php';
      for (const [name, value] of Object.entries({csrf: app.dataset.csrf, node: app.dataset.node,
        id: ses.id, action: ses.state === 'pending' ? 'claim' : 'close'})) {
        const campo = document.createElement('input');
        campo.type = 'hidden'; campo.name = name; campo.value = value; frm.append(campo);
      }
      const enviar = document.createElement('button');
      enviar.textContent = ses.state === 'pending' ? 'Accept request' : 'Close assistance'; frm.append(enviar);
      fila.append(codigo, estado, frm);
      if (ses.state === 'ready' && /^[a-f0-9]{32}$/.test(ses.id)) {
        const abrir = document.createElement('a'); abrir.className = 'terminal-open';
        abrir.href = 'terminal.php?' + new URLSearchParams({node: app.dataset.node, session: ses.id});
        abrir.target = '_blank'; abrir.rel = 'noopener noreferrer';
        abrir.textContent = 'Open two terminals ↗'; fila.append(abrir);
      }
      filas.push(fila);
    }
    // Polling this page must never open or take over a terminal window.
    lista.replaceChildren(...filas);
  }
  async function poll() {
    if (con_act) return;
    con_act = true;
    try {
      const res = await fetch('cli.php', {method: 'POST', credentials: 'same-origin', cache: 'no-store',
        body: new URLSearchParams({action: 'status', node: app.dataset.node, csrf: app.dataset.csrf})});
      const dat = await res.json();
      if (!res.ok) throw new Error(dat.error || 'Verify the second factor to load requests.');
      for (const ses of dat.sessions.filter(s => s.state === 'pending' && !seen.has(s.code))) {
        seen.add(ses.code);
        if ('Notification' in window && Notification.permission === 'granted')
          new Notification('New assistance request', {body: ses.code});
      }
      muestra_sesiones(dat.sessions);
      state.textContent = `${dat.sessions.length} requests · ${dat.node} · Connected`;
    } catch (err) {state.textContent = err.message;}
    finally {con_act = false;}
  }
  setInterval(poll, 5000); poll();
})();
