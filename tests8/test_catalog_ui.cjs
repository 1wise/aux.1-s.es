// Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
// Author & Credits: https://www.alawise.es/1-s
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {JSDOM}=require(process.env.AUX_JSDOM||'jsdom');
const root=path.resolve(__dirname,'..');
const rsp=spawnSync('python3',['-c',"from auxlib.webapps import modelo,pagina; print(pagina('catalogue',modelo()))"],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024});
assert.equal(rsp.status,0,rsp.stderr);
const script=fs.readFileSync(path.join(root,'ui/workspace.js'),'utf8');
function crea(){
  const dom=new JSDOM(rsp.stdout,{runScripts:'outside-only',url:'https://aux.example/catalogue.html'});
  const win=dom.window;win.structuredClone=structuredClone;win.Blob=Blob;
  let blob;const errors=[];
  win.URL.createObjectURL=x=>{blob=x;return 'blob:test';};win.URL.revokeObjectURL=()=>{};
  win.HTMLAnchorElement.prototype.click=function(){};
  win.addEventListener('error',e=>errors.push(e.message));win.eval(script);
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
  let dat=await app.exporta();const gentoo=dat.entries.find(e=>e.id==='gentoo-stage3-amd64-openrc');assert.equal(gentoo.policy,'A16');
  const policy=doc.querySelector('input[aria-label="Política CDE de gentoo-stage3-amd64-openrc"]');
  policy.value='A04';policy.dispatchEvent(new app.win.Event('input',{bubbles:true}));
  doc.querySelector('#catalog-presets input[value=fedora]').click();
  dat=await app.exporta();assert.equal(dat.entries.find(e=>e.id===gentoo.id).policy,'A04');
  const ram=doc.querySelector('input[aria-label="gentoo-stage3-amd64-openrc · RAM"]');ram.click();
  const bastion=doc.querySelector('input[aria-label="gentoo-stage3-amd64-openrc · Bastion"]');bastion.click();
  dat=await app.exporta();assert.equal(parseInt(dat.entries.find(e=>e.id===gentoo.id).policy,16)&9,9);
  assert.equal(doc.querySelectorAll('#export-light,#export-heavy').length,0);
  assert.deepEqual(app.errors,[]);app.dom.window.close();
  console.log('AUX 8 DOM: three cumulative presets, shared chroot, manual edits, multiple locations and canonical export passed.');
})().catch(err=>{console.error(err);process.exitCode=1;});
