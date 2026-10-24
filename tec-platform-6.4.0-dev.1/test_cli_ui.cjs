// Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
// Author and Credits: https://www.alawise.es/1-s
// Exercise request polling without creating a terminal in the parent page.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class Element {
  constructor(tag) {this.tagName=tag;this.children=[];this.dataset={};this.events={};this.textContent='';}
  append(...nodes) {for(const n of nodes){n.parent=this;this.children.push(n);}}
  replaceChildren(...nodes) {this.children=[];this.append(...nodes);}
  addEventListener(name,fn) {this.events[name]=fn;}
}
function all(el) {return [el,...el.children.flatMap(all)];}
const nodes=Object.fromEntries(['cli-app','cli-state','sessions','notify-enable'].map(id=>[id,new Element('div')]));
nodes['cli-app'].dataset={url:'https://cli.example.test',node:'excalibur',csrf:'fixture-csrf'};
const id='a'.repeat(32);
let sesiones=[{id,code:'AUX-FIXTURE',state:'awaiting_client'}],poll,requests=0;
const document={getElementById:id=>nodes[id],createElement:tag=>new Element(tag),
  querySelectorAll:()=>all(nodes.sessions).filter(n=>n.tagName==='h3')};
const context=vm.createContext({document,window:{},URLSearchParams,console,
  setInterval:fn=>{poll=fn;return 1;},
  fetch:async(url,opts)=>{
    requests++;assert.equal(url,'cli.php');assert.equal(opts.body.get('action'),'status');
    assert.equal(opts.body.get('csrf'),'fixture-csrf');assert.equal(opts.body.get('node'),'excalibur');
    return {ok:true,json:async()=>({node:'excalibur',sessions:sesiones})};
  }});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  vm.runInContext(fs.readFileSync(path.join(__dirname,'web/cli.js'),'utf8'),context);
  await flush();assert(!all(nodes.sessions).some(n=>n.className==='terminal-open'));
  sesiones=[{id,code:'AUX-FIXTURE',state:'ready'}];await poll();
  const button=all(nodes.sessions).find(n=>n.className==='terminal-open');assert(button);
  assert.equal(button.tagName,'a');assert.equal(button.target,'_blank');assert.equal(button.rel,'noopener noreferrer');
  const url=new URL(button.href,'https://tec.example.test/');
  assert.equal(url.pathname,'/terminal.php');assert.equal(url.searchParams.get('session'),id);
  assert.equal(url.searchParams.get('node'),'excalibur');assert(!button.href.includes('ticket'));
  sesiones=[{id,code:'AUX-FIXTURE',state:'active'}];await poll();
  assert(all(nodes.sessions).some(n=>n.textContent==='Terminal workspace open'));
  assert(!all(nodes.sessions).some(n=>n.className==='terminal-open'));
  sesiones=[{id,code:'<img src=x onerror=alert(1)>',state:'pending'}];await poll();
  assert(all(nodes.sessions).some(n=>n.tagName==='h3'&&n.textContent===sesiones[0].code));
  assert(!all(nodes.sessions).some(n=>n.tagName==='img'));
  sesiones=[];await poll();assert(!all(nodes.sessions).some(n=>n.tagName==='article'));assert(requests>=5);
  console.log('PASS: request polling, safe labels, user-initiated new-tab links and no parent terminal/tickets');
})().catch(err=>{console.error(err);process.exitCode=1;});
