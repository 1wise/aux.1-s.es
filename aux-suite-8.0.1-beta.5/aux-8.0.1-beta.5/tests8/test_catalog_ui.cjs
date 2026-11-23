// Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
// Author & Credits: https://www.alawise.es/1-s
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {JSDOM}=require(process.env.AUX_JSDOM||'jsdom');
const root=path.resolve(__dirname,'..');
const rsp=spawnSync('python3',['-c',"from auxlib.webapps import modelo,pagina; print(pagina('catalogue',modelo()))"],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024});
assert.equal(rsp.status,0,rsp.stderr);
const script=fs.readFileSync(path.join(root,'ui/workspace.js'),'utf8');
function crea(saved=[]){
  const dom=new JSDOM(rsp.stdout,{runScripts:'outside-only',url:'https://aux.example/catalogue.html'});
  const win=dom.window;win.structuredClone=structuredClone;win.Blob=Blob;
  let blob;const errors=[];
  win.URL.createObjectURL=x=>{blob=x;return 'blob:test';};win.URL.revokeObjectURL=()=>{};
  win.HTMLAnchorElement.prototype.click=function(){};
  win.addEventListener('error',e=>errors.push(e.message));for(const [k,v] of saved)win.sessionStorage.setItem(k,v);win.eval(fs.readFileSync(path.join(root,'ui/status.js'),'utf8'));win.eval(script);
  return {dom,win,doc:win.document,errors,exporta:async()=>{
    win.document.getElementById('export-catalog').click();assert.ok(blob);return JSON.parse(await blob.text());
  }};
}
(async()=>{
  for(const preset of ['alpine','fedora','debian']){
    const app=crea();app.doc.querySelector('#catalog-presets input[value='+preset+']').click();
    const dat=await app.exporta();assert.equal(dat.schema,'aux-catalog-v8');
    assert.ok(dat.entries.some(e=>e.id==='gentoo-stage3-amd64-openrc'));
    assert.equal(dat.entries.length,new Set(dat.entries.map(e=>e.id)).size);
    assert.deepEqual(app.errors,[]);app.dom.window.close();
  }
  const app=crea(),doc=app.doc;
  doc.querySelector('#catalog-presets input[value=todos]').click();
  assert.ok([...doc.querySelectorAll('#catalog-presets input')].every(e=>e.checked));
  let dat=await app.exporta();assert.equal(dat.planning.presets.length,3);assert.equal(dat.planning.preset_ram_gib,10);assert.equal(dat.planning.preset_ssd_gib,75);assert.equal(doc.querySelector('#capacity-rows tr td:nth-child(5)').textContent,'30.00');assert.ok(Number(doc.querySelectorAll('#capacity-rows tr')[1].children[3].textContent)<=225);const gentoo=dat.entries.find(e=>e.id==='gentoo-stage3-amd64-openrc');assert.equal(gentoo.policy,'A16');
  doc.querySelector('[data-resource=gentoo-stage3-amd64-openrc] [data-action=info]').click();
  const policy=doc.querySelector('input[aria-label="Política CDE de gentoo-stage3-amd64-openrc"]');
  policy.value='A04';policy.dispatchEvent(new app.win.Event('input',{bubbles:true}));
  doc.querySelector('#catalog-presets input[value=fedora]').click();
  dat=await app.exporta();assert.equal(dat.entries.find(e=>e.id===gentoo.id).policy,'A04');
  const ram=doc.querySelector('[data-resource=gentoo-stage3-amd64-openrc] input[data-bit="0"]');ram.click();
  const bastion=doc.querySelector('[data-resource=gentoo-stage3-amd64-openrc] input[data-bit="3"]');bastion.click();
  dat=await app.exporta();assert.equal(parseInt(dat.entries.find(e=>e.id===gentoo.id).policy,16)&9,9);
  assert.equal(doc.querySelectorAll('#export-light,#export-heavy').length,0);
  const peer=crea(Object.entries(app.win.sessionStorage));const recalled=await peer.exporta();assert.equal(recalled.entries.find(e=>e.id===gentoo.id).policy,dat.entries.find(e=>e.id===gentoo.id).policy);assert.deepEqual(peer.errors,[]);peer.win.close();
  const fixture={id:'one',family:'gentoo',deploy_method:'chroot',procedure_url:'https://example.org/',policy:'01F',size_bytes:1073741824,artifact_type:'iso'};
  const cfg={ram_budget_gib:30,ssd_budget_gib:225,ram_reserve_percent:0,preset_ram_gib:10,preset_ssd_gib:75,ssd_mode:'extract'};
  const cli=spawnSync('python3',['-c',"import json;from auxlib.capacity import prevision;print(json.dumps(prevision("+JSON.stringify([fixture])+","+JSON.stringify(cfg)+",['alpine','fedora','debian'])))"],{cwd:root,encoding:'utf8'});
  assert.equal(cli.status,0,cli.stderr);const expected=JSON.parse(cli.stdout),actual=app.win.AUXCapacity([fixture],cfg,['alpine','fedora','debian']);
  for(const key of ['images_bytes','deploy_bytes','cache_bytes','selected_bytes','budget_bytes','remaining_bytes','shared_savings_bytes','unknown_sizes','estimated_deployments','over_budget'])assert.equal(JSON.stringify(actual[key]),JSON.stringify(expected[key]),key);
  assert.deepEqual(app.errors,[]);app.dom.window.close();
  console.log('AUX 8 DOM: three cumulative presets, shared chroot, manual edits, multiple locations and canonical export passed.');
})().catch(err=>{console.error(err);process.exitCode=1;});
