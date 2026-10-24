// Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
// Author & Credits: https://www.alawise.es/1-s
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class Element {
  constructor(tag) {this.tagName=tag;this.children=[];this.dataset={};this.textContent='';}
  append(...ent) {this.children.push(...ent);}
  replaceChildren(...ent) {this.children=ent;}
}
const reg=new Element('main'),lst=new Element('div'),msg=new Element('p');
reg.dataset.csrf='fixture-csrf';
const cas=new Element('span'),ent=new Element('span'),not=new Element('textarea');
cas.dataset={caseId:'fixture:one',state:'ready'};ent.dataset={caseId:'fixture:closed',state:'closed'};
not.textContent='Work note draft';
const nodes={'registry-app':reg,'connection-list':lst,'registry-state':msg};
let dat={nodes:{fixture:'online'},cases:[{id:'fixture:one',title:'<script>fixture</script>',connection:'ready',last_seen:1}]};
let err=false,poll;
const document={getElementById:id=>nodes[id],createElement:tag=>new Element(tag),
  querySelectorAll:sel=>sel==='[data-case-id]'?[cas,ent]:[]};
const context=vm.createContext({document,URLSearchParams,Date,console,
  setInterval:fn=>{poll=fn;},fetch:async(url,cfg)=>{
    assert.equal(cfg.body.get('csrf'),'fixture-csrf');assert.equal(cfg.body.get('action'),'sync');
    return {ok:!err,json:async()=>err?{error:'Second factor expired'}:dat};
  }});
const flush=()=>new Promise(res=>setImmediate(res));
(async()=>{
  vm.runInContext(fs.readFileSync(path.join(__dirname,'web/cases.js'),'utf8'),context);await flush();
  assert.equal(cas.textContent,'Gateway connected');assert.equal(lst.children[0].textContent,'<script>fixture</script>');
  assert.equal(lst.children[0].tagName,'a');assert.equal(lst.children[0].children[0].tagName,'span');
  dat.cases[0].connection='reconnecting';await poll();
  assert.equal(cas.textContent,'Waiting for client / reboot');assert.equal(not.textContent,'Work note draft');
  dat.nodes.fixture='unavailable';dat.cases[0].connection='unknown';await poll();
  assert.equal(cas.textContent,'Status unknown');
  err=true;await poll();assert.equal(msg.textContent,'Second factor expired');
  assert.equal(ent.dataset.state,'closed');assert.equal(not.textContent,'Work note draft');
  console.log('PASS: safe live status, reconnect/offline/TOTP states and retained note drafts (Node DOM fixture)');
})().catch(err=>{console.error(err);process.exitCode=1;});
