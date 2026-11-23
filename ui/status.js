// Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
// Author & Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  if(document.body.dataset.app!=='status')return;
  const dat=JSON.parse(document.getElementById('workspace-data').textContent),estado=dat.status;
  const el=id=>document.getElementById(id),txt=(tag,s)=>{const n=document.createElement(tag);n.textContent=s;return n;};
  let limite=25;
  const aviso=s=>{el('app-status').textContent=s;el('app-status').hidden=false;};
  function guarda(nom,dat){const url=URL.createObjectURL(new Blob([JSON.stringify(dat,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=nom;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function ficha(ent,obs){
    const det=document.createElement('details');det.className='resource-info';det.append(txt('summary','Info · ficha completa'));
    const dl=document.createElement('dl');dl.className='resource-fields';
    for(const [nom,val] of [['ID',ent.id],['Versión',ent.release],['Arquitectura',ent.architecture],['Tipo de artefacto',ent.artifact_type],['SHA-256',ent.sha256||'Pendiente de resolver'],['Tamaño',ent.size_bytes||'Desconocido'],['Política CDE',ent.policy],['URL comprobada',obs.url_check?.status||'Sin comprobar'],['Fecha HTTP',obs.url_check?.checked_at||'Sin observación'],['Prueba de login',obs.boot_test?.status||'not-tested']]){dl.append(txt('dt',nom),txt('dd',String(val)));}
    det.append(dl);
    for(const [rot,url] of [['Origen exacto',ent.original_url],['Índice de versiones',ent.source_index],['Procedimiento',ent.procedure_url]])if(url){const a=txt('a',rot);a.href=url;a.rel='noopener noreferrer';det.append(a,txt('span',' '));}
    if((parseInt(ent.policy,16)&128)!==0)det.append(txt('p','Archivar implica conservación, aunque la casilla Conservar esté desmarcada.'));
    const pre=txt('pre',JSON.stringify({resource:ent,observations:obs},null,2));det.append(pre);return det;
  }
  function pinta(){
    const q=el('status-search').value.toLowerCase(),lista=dat.entries.filter(e=>[e.name,e.id,e.release,e.architecture,e.original_url].join(' ').toLowerCase().includes(q));
    const frag=document.createDocumentFragment();
    for(const ent of lista.slice(0,limite)){
      const obs=estado.entries[ent.id]||{word24:'000000',known_observation_mask:'00000'},card=document.createElement('article');card.className='panel status-resource';card.dataset.resource=ent.id;
      card.append(txt('h2',ent.name||ent.id),txt('p',ent.release+' · '+ent.architecture));
      const word=txt('output','');word.className='word24';word.setAttribute('aria-label','RASCDE '+ent.id);
      const base=parseInt(obs.word24||'000000',16)&0xff000,known=parseInt(obs.known_observation_mask||'00000',16);
      const actualiza=()=>{word.textContent=(base|parseInt(ent.policy,16)).toString(16).toUpperCase().padStart(6,'0');obs.word24=word.textContent;};actualiza();card.append(word);
      const scroll=document.createElement('div');scroll.className='bits-scroll';const fila=document.createElement('div');fila.className='bits20';fila.setAttribute('aria-label','20 bits de '+ent.id);
      for(const g of estado.groups){const grupo=document.createElement('fieldset');grupo.className='bit-group';grupo.append(txt('legend',g.id+' · '+g.label));
        for(const b of estado.bits.filter(b=>b.group===g.id)){
          const lab=document.createElement('label');lab.className='bit-cell';lab.append(txt('small',String(b.bit)),txt('span',b.label));
          const box=document.createElement('input');box.type='checkbox';box.dataset.bit=b.bit;box.setAttribute('aria-label',ent.id+' · '+g.id+' · '+b.label+' · bit '+b.bit);
          box.checked=!!((base|parseInt(ent.policy,16))&(1<<b.bit));box.disabled=b.readonly||(ent.remote_only&&b.group==='E'&&b.bit!==2);
          if(b.readonly&&!(known&(1<<b.bit))){box.indeterminate=true;lab.title='Sin observación vigente; no equivale a ausencia.';}
          box.addEventListener('change',()=>{let n=parseInt(ent.policy,16);n=box.checked?n|(1<<b.bit):n&~(1<<b.bit);ent.policy=n.toString(16).toUpperCase().padStart(3,'0');actualiza();const old=card.querySelector('details');const fresh=ficha(ent,obs);fresh.open=old.open;old.replaceWith(fresh);});lab.append(box);grupo.append(lab);
        }fila.append(grupo);
      }scroll.append(fila);card.append(scroll,ficha(ent,obs));frag.append(card);
    }el('status-rows').replaceChildren(frag);el('status-more').hidden=lista.length<=limite;
  }
  const aud=estado.audit||{};el('audit-summary').textContent=aud.checked_at?'Última revisión HTTP: '+aud.checked_at+' · '+(aud.summary?.verified||0)+' URL verificadas de '+(aud.summary?.total||0)+' · revisión semanal.':'Sin revisión HTTP publicada. No se presume disponibilidad.';
  el('status-search').addEventListener('input',()=>{limite=25;pinta();});el('status-more').addEventListener('click',()=>{limite+=25;pinta();});
  el('status-export').addEventListener('click',()=>guarda('catalog.json',window.AUXCatalog.document(dat.entries)));
  el('status-snapshot').addEventListener('click',()=>guarda('status-public.json',estado));
  el('status-import').addEventListener('change',async evt=>{try{
    const file=evt.target.files[0];if(!file||file.size>2*1024*1024)throw Error('Elegir una instantánea JSON de hasta 2 MiB.');
    const snap=JSON.parse(await file.text());if(snap.schema!=='aux-status-v1'||!Array.isArray(snap.entries))throw Error('Se requiere la salida de aux checkstatus.');
    const fresh=Date.now()-Date.parse(snap.checked_at);if(!Number.isFinite(fresh)||fresh<0||fresh>3600000)throw Error('La instantánea ha caducado; ejecutar checkstatus de nuevo.');
    const cambios=[];
    for(const row of snap.entries){const ent=dat.entries.find(e=>e.id===row.id);if(!ent)continue;
      if(!/^[0-9A-F]{6}$/i.test(row.word24)||parseInt(row.word24,16)>0xfffff)throw Error('Palabra RASCDE inválida.');
      if(ent.identity&&row.identity!==ent.identity)throw Error('La instantánea corresponde a otro artefacto: '+row.id);
      if(row.identity&&ent.identity)cambios.push([row.id,{word24:row.word24,known_observation_mask:'FF000',checked_at:row.checked_at,boot_test:{status:row.boot_test?.status||'not-tested'}}]);
    }if(!cambios.length)throw Error('No hay observaciones del catálogo actual.');
    for(const [id,obs] of cambios)Object.assign(estado.entries[id],obs);
    pinta();aviso('Observaciones cargadas; las políticas CDE se conservan.');
  }catch(e){aviso(e.message);}});
  pinta();
})();
