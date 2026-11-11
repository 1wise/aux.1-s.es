// Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
// Author & Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  const reg = document.getElementById('registry-app');
  const lst = document.getElementById('connection-list');
  if (!reg || !lst) return;
  let sync_act = false;
  const est = {ready: 'Gateway connected', active: 'Web terminal open', reconnecting: 'Waiting for client / reboot',
    awaiting_resume: 'Restoring authorization', awaiting_client: 'Waiting for client consent',
    closed: 'Authorization closed', expired: 'Authorization expired', unknown: 'Status unknown',
    unavailable: 'Case unavailable', unmonitored: 'Direct C / offline · manual tracking'};
  const msg = document.getElementById('registry-state');
  function fecha(tms_act) {
    return tms_act ? new Date(tms_act * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC') : 'Not observed';
  }
  async function poll() {
    if (sync_act) return;
    sync_act = true;
    try {
      const dat = await fetch('cases.php', {method: 'POST', credentials: 'same-origin', cache: 'no-store',
        body: new URLSearchParams({action: 'sync', format: 'json', csrf: reg.dataset.csrf})});
      const res = await dat.json();
      if (!dat.ok) throw new Error(res.error || 'Sign in and verify the second factor.');
      for (const ent of document.querySelectorAll('[data-case-id]')) {
        const ses = res.cases.find(ses => ses.id === ent.dataset.caseId);
        if (ses) {ent.textContent = est[ses.connection] || ses.connection; ent.dataset.state = ses.connection;}
      }
      for (const ent of document.querySelectorAll('[data-seen-id]')) {
        const ses = res.cases.find(ses => ses.id === ent.dataset.seenId);
        if (ses) ent.textContent = fecha(ses.last_seen);
      }
      // Replace only the connection watch; drafts, filters and notes keep their focus.
      const ent = res.cases.filter(ses => !['closed', 'expired', 'unmonitored'].includes(ses.connection)).slice(-20).map(ses => {
        const clt = document.createElement('a'); clt.href = 'cases.php?case=' + encodeURIComponent(ses.id);
        clt.textContent = ses.title;
        const txt = document.createElement('span'); txt.textContent = est[ses.connection] || ses.connection;
        clt.append(txt); return clt;
      });
      lst.replaceChildren(...ent);
      const txt = Object.entries(res.nodes).map(([nom, val]) => nom + ': ' + val).join(' · ');
      msg.textContent = (txt || 'No gateway configured. Local case records remain available.') + ' · Checked ' + fecha(Date.now() / 1000);
    } catch (err) {
      msg.textContent = err.message;
      for (const ent of document.querySelectorAll('[data-case-id]')) {
        if (!['closed', 'expired', 'unmonitored'].includes(ent.dataset.state)) {
          ent.textContent = 'Status unknown'; ent.dataset.state = 'unknown';
        }
      }
    } finally {sync_act = false;}
  }
  setInterval(poll, 5000); poll();
})();
