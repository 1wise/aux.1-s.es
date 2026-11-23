// Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
// Author & Credits: https://www.alawise.es/1-s
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {JSDOM}=require(process.env.AUX_JSDOM||'jsdom');
const root=path.resolve(__dirname,'..');
const ret=spawnSync('python3',['-c',"from auxlib.webapps import modelo,pagina; print(pagina('status',modelo()))"],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024});
assert.equal(ret.status,0,ret.stderr);
const dom=new JSDOM(ret.stdout,{runScripts:'outside-only',url:'https://aux.example/status.html'}),win=dom.window,doc=win.document;
win.structuredClone=structuredClone;win.Blob=Blob;let blob;const errors=[];
win.addEventListener('error',e=>errors.push(e.message));win.URL.createObjectURL=x=>{blob=x;return 'blob:test';};win.URL.revokeObjectURL=()=>{};win.HTMLAnchorElement.prototype.click=function(){};
for(const file of ['status.js','workspace.js'])win.eval(fs.readFileSync(path.join(root,'ui',file),'utf8'));
(async()=>{
  const first=doc.querySelector('.status-resource'),boxes=[...first.querySelectorAll('.bit-checkbox')];
  assert.equal(boxes.length,24);assert.deepEqual(boxes.map(e=>+e.dataset.bit),Array.from({length:24},(_,i)=>23-i));
  assert.equal(boxes.filter(e=>e.disabled).length,8);assert.ok(boxes.find(e=>e.dataset.bit==='15').indeterminate);
  const info=first.querySelector('[data-action=info]');info.click();const ram=boxes.find(e=>e.dataset.bit==='0');ram.click();
  assert.equal(info.getAttribute('aria-expanded'),'true');assert.equal(parseInt(first.querySelector('output').textContent,16)&1,ram.checked?1:0);
  const user=boxes.find(e=>e.dataset.bit==='20'),required=boxes.find(e=>e.dataset.bit==='22');user.click();required.click();assert.equal(first.querySelector('output').textContent[0],'5');
  doc.getElementById('status-export').click();const cat=JSON.parse(await blob.text());
  assert.equal(cat.schema,'aux-catalog-v8');assert.equal(cat.entries.find(e=>e.id===first.dataset.resource).priority,'5');assert.ok(cat.entries.every(e=>!('word24' in e)&&!('url_check' in e)&&!('identity' in e)));
  assert.equal(cat.entries.find(e=>e.id==='aux-debian-netboot-amd64').recipe_owner,'AUX');
  assert.equal(cat.entries.find(e=>e.id===first.dataset.resource).policy,first.querySelector('output').textContent.slice(-3));
  const raw=JSON.parse(doc.getElementById('workspace-data').textContent),ent=raw.entries.find(e=>e.id===first.dataset.resource);
  let snap={schema:'aux-status-v1',checked_at:new Date().toISOString(),entries:[{id:ent.id,identity:ent.identity,word24:'088004',boot_test:{status:'passed'}}]};
  const input=doc.getElementById('status-import');Object.defineProperty(input,'files',{value:[{size:500,text:async()=>JSON.stringify(snap)}]});
  input.dispatchEvent(new win.Event('change'));await new Promise(r=>setImmediate(r));
  assert.equal(doc.querySelector('.status-resource input[data-bit="15"]').checked,true);assert.equal(doc.querySelector('.status-resource output').textContent[0],'5');
  assert.equal(doc.querySelector('.status-resource output').textContent.slice(-3),cat.entries.find(e=>e.id===ent.id).policy);
  snap={...snap,entries:[{...snap.entries[0],identity:'wrong'}]};input.dispatchEvent(new win.Event('change'));await new Promise(r=>setImmediate(r));
  assert.match(doc.getElementById('app-status').textContent,/otro artefacto/);
  assert.equal(first.tagName,'TR');doc.querySelector('[data-board-task=download]').click();assert.match(doc.getElementById('workflow-command').textContent,/download --catalog catalog.json --dry-run/);
  assert.deepEqual(errors,[]);win.close();
  console.log('Status DOM: 24 ordered bits, eight observed, editable P/CDE, full info, canonical export and pinned snapshot import passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
