// Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
// Author & Credits: https://www.alawise.es/1-s
'use strict';
// Exercise real DOM events and exported files; native installation remains a VM check.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const {JSDOM}=require(process.env.AUX_JSDOM||'jsdom');
const dir_app=path.resolve(__dirname,'..');
function python(cod,txt=''){
  const res=spawnSync('python3',['-c',cod],{cwd:dir_app,input:txt,encoding:'utf8',maxBuffer:4*1024*1024});
  assert.equal(res.status,0,res.stderr);return res.stdout;
}
const pag=python("from auxlib.webapps import modelo,pagina; print(pagina('installer',modelo()))");
const dom=new JSDOM(pag,{runScripts:'outside-only',url:'https://aux.example/installer.html'});
const win=dom.window,doc=win.document;
const errores=[];
win.addEventListener('error',evt=>errores.push(evt.message));
win.structuredClone=structuredClone;win.Blob=Blob;
let ult_blob;
win.URL.createObjectURL=val=>{ult_blob=val;return 'blob:aux-test';};
win.URL.revokeObjectURL=()=>{};
win.HTMLAnchorElement.prototype.click=function(){};
win.eval(fs.readFileSync(path.join(dir_app,'ui/workspace.js'),'utf8'));
const nodo=nom=>doc.getElementById(nom);
function cambia(nom,val){nodo(nom).value=val;nodo(nom).dispatchEvent(new win.Event('input',{bubbles:true}));nodo(nom).dispatchEvent(new win.Event('change',{bubbles:true}));}
function busca(txt){nodo('software-search').value=txt;nodo('software-search').dispatchEvent(new win.Event('input',{bubbles:true}));}
async function descarga(nom){ult_blob=null;nodo(nom).click();assert.ok(ult_blob);return ult_blob.text();}
async function verifica_exportacion(){
  const txt=await descarga('download-selection');
  const dat=JSON.parse(txt);
  const res=JSON.parse(python(`import json,sys,tempfile
from pathlib import Path
from auxlib import profiles,interactive
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'selection.json').write_text(sys.stdin.read())
    c=interactive.lee_seleccion(p/'selection.json')
    d=profiles.genera(c['distro'],c['roles'].split(','),p/'profile',native=c['native'],identity=c.get('identity'))
    n='installed.ks' if c['distro']=='fedora' else 'apply-alpine.sh' if c['distro']=='alpine' else 'preseed.cfg'
    print(json.dumps({'profile':(p/'profile'/n).read_text(),'selection':d}))`,txt));
  assert.equal((await descarga('download-profile')).trimEnd(),res.profile.trimEnd());
  const paq=nodo('selected-packages').textContent.split('\n');
  assert.deepEqual(paq,res.selection.packages);
  return dat;
}
(async()=>{
  assert.equal(nodo('install-mode').value,'iso');
  assert.equal(nodo('install-mode').options[nodo('install-mode').options.length-1].value,'existing');
  assert.ok(nodo('install-mode').options[nodo('install-mode').options.length-1].textContent.includes('SISTEMA ACTUAL'));
  cambia('install-mode','root');
  const asist=doc.querySelector('input[name=role][value="aux-assist"]');
  assert.ok(asist);assert.equal(asist.checked,false);
  assert.ok(!(await verifica_exportacion()).roles.includes('aux-assist'));
  asist.click();assert.ok((await verifica_exportacion()).roles.includes('aux-assist'));
  asist.click();assert.ok(!(await verifica_exportacion()).roles.includes('aux-assist'));
  asist.click();
  assert.equal(doc.querySelectorAll('input[name=native]').length,230);
  assert.equal(doc.querySelectorAll('input[name=role][value=desktop]').length,0);
  busca('amharic');
  const amh=doc.querySelector('input[name=native][value=amharic]');
  assert.equal(amh.closest('label').hidden,false);amh.click();
  const deb=await verifica_exportacion();assert.ok(deb.native.tasks.includes('amharic'));
  cambia('distribution','fedora');
  assert.equal(doc.querySelectorAll('input[name=native]').length,155);
  assert.equal(nodo('native-environment').options.length,21);
  cambia('native-environment','server-product-environment');
  const req=doc.querySelector('input[name=native][value=server-product]');
  assert.equal(req.checked,true);assert.equal(req.disabled,true);
  busca('container-management');
  const con=doc.querySelector('input[name=native][value=container-management]');
  assert.equal(con.closest('label').hidden,false);con.click();
  const fed=await verifica_exportacion();
  assert.equal(fed.native.environment,'server-product-environment');
  assert.ok(fed.native.groups.includes('server-product'));
  assert.ok(fed.native.groups.includes('container-management'));
  assert.ok(!nodo('selected-packages').textContent.includes('@xfce-desktop'));
  busca('');nodo('software-advanced').click();
  assert.equal(Array.from(nodo('native-options').querySelectorAll('label')).filter(ent=>!ent.hidden).length,155);
  cambia('distribution','alpine');
  assert.ok(nodo('software-source').textContent.includes('colecciones AUX / apk'));
  assert.equal(nodo('environment-field').hidden,true);
  const alp=await verifica_exportacion();
  assert.equal(alp.distribution,'alpine');
  assert.ok(alp.native.groups.includes('base'));
  assert.ok(nodo('selected-packages').textContent.includes('alpine-base'));
  assert.ok(!nodo('selected-packages').textContent.includes('@'));
  const red=doc.querySelector('input[name=native][value=network]');red.click();
  assert.ok((await verifica_exportacion()).native.groups.includes('network'));
  cambia('distribution','debian');
  assert.equal(doc.querySelector('input[name=native][value=amharic]').checked,true);
  cambia('install-mode','existing');
  assert.ok(nodo('target-description').textContent.includes('SISTEMA ACTUAL'));
  assert.ok(nodo('target-description').textContent.includes('puede modificar sus servicios'));
  assert.ok(nodo('apply-heading').textContent.includes('SISTEMA ACTUAL'));
  assert.equal((await verifica_exportacion()).root,'/');
  nodo('identity-apply').click();
  cambia('identity-hostname','Cari.Lab');cambia('identity-user','enki');
  for(const dis of ['debian','fedora','alpine']){cambia('distribution',dis);const dat=await verifica_exportacion();assert.equal(dat.identity.hostname,'cari.lab');assert.equal(dat.identity.user,'enki');}
  cambia('identity-user','root');nodo('download-selection').click();assert.equal(nodo('setup-error').hidden,false);cambia('identity-user','enki');
  cambia('install-mode','iso');nodo('download-selection').click();
  assert.equal(nodo('setup-error').hidden,false);
  cambia('install-mode','kernel-modeler');
  assert.equal(nodo('kernel-modeler-fields').hidden,false);
  for(const dis of ['debian','fedora','alpine']){
    cambia('distribution',dis);
    const data=await verifica_exportacion();assert.equal(data.mode,'kernel-modeler');assert.equal(data.target_mode,'root');
    assert.ok(data.roles.includes('kernel-modeler'));assert.ok(!data.roles.includes('aux-assist'));
    assert.equal(doc.querySelector('input[name=role][value=kernel-modeler]').disabled,true);
    if(dis==='debian')assert.deepEqual(data.native.tasks,['standard']);
    if(dis==='fedora'){assert.equal(data.native.environment,'');assert.ok(data.native.groups.includes('core'));}
    assert.ok(nodo('selected-packages').textContent.includes(dis==='alpine'?'qemu-system-x86_64':dis==='fedora'?'qemu-system-x86-core':'qemu-system-x86'));
  }
  cambia('kernel-target-mode','iso');cambia('iso-path','/srv/iso/input.iso');cambia('iso-sha','a'.repeat(64));
  assert.equal((await verifica_exportacion()).target_mode,'iso');assert.ok(nodo('setup-apply').textContent.includes('--check-packages'));
  cambia('kernel-target-mode','existing');assert.equal((await verifica_exportacion()).target_mode,'existing');assert.ok(nodo('target-description').textContent.includes('SISTEMA ACTUAL'));
  assert.deepEqual(errores,[]);
  console.log('PASS: ISO default; host last and explicit; optional aux-assist; native catalogs; validation; exports match Python');
  win.close();
})().catch(exc=>{console.error(exc);win.close();process.exitCode=1;});
