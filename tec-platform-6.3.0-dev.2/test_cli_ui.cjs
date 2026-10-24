// Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
// Author & Credits: https://www.alawise.es/1-s
// Exercise the unmodified browser script with a small DOM/event fixture in Node.
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
  closest(selector) {return selector==='.terminal-open'&&this.className==='terminal-open'?this:this.parent?.closest(selector);}
}
function all(el) {return [el,...el.children.flatMap(all)];}
const nodes=Object.fromEntries(['cli-app','cli-state','sessions','terminal-paste','terminal'].map(id=>[id,new Element('div')]));
nodes['cli-app'].dataset={url:'https://cli.example.test',node:'excalibur',csrf:'fixture-csrf'};
const id='a'.repeat(32);
let sesiones=[{id,code:'AUX-FIXTURE',state:'awaiting_client'}],poll,ticket,terminal,disposed=0,ws;
const document={getElementById:id=>nodes[id],createElement:tag=>new Element(tag),
  querySelectorAll:()=>all(nodes.sessions).filter(n=>n.tagName==='h3')};
class Terminal {
  constructor(){terminal=this;}
  open(el){this.node=new Element('terminal');el.append(this.node);}
  dispose(){disposed++;} focus(){} onData(){} onBinary(){} onResize(){}
}
class WebSocket {
  static OPEN=1;
  constructor(url){ws=this;this.url=url;this.readyState=0;queueMicrotask(()=>{this.readyState=1;this.onopen?.();
    this.onmessage?.({data:JSON.stringify({type:'ready'})});});}
  send(){} close(){this.readyState=3;this.onclose?.();}
}
const window={Terminal,location:{search:'?session='+id},addEventListener(){}};
const context=vm.createContext({document,window,Terminal,WebSocket,URLSearchParams,TextEncoder,
  ArrayBuffer,Uint8Array,console,navigator:{},setInterval:(fn,ms)=>{if(ms===5000)poll=fn;return 1;},clearInterval(){},
  fetch:async(url,opts)=>{
    assert.equal(opts.body.get('csrf'),'fixture-csrf');assert.equal(opts.body.get('node'),'excalibur');
    if(opts.body.get('action')==='ticket'){ticket=opts.body.get('id');return {ok:true,json:async()=>({ticket:'fixture'})};}
    return {ok:true,json:async()=>({node:'excalibur',sessions:sesiones})};
  }});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  vm.runInContext(fs.readFileSync(path.join(__dirname,'web/cli.js'),'utf8'),context);
  await flush();
  assert(all(nodes.sessions).some(n=>n.textContent==='Esperando autorización del cliente'));
  assert(!all(nodes.sessions).some(n=>n.className==='terminal-open'));
  sesiones=[{id,code:'AUX-FIXTURE',state:'ready'}];await poll();await flush();
  assert.equal(ticket,id,'Dashboard link selects the authorized case');
  const button=all(nodes.sessions).find(n=>n.className==='terminal-open');assert(button);
  nodes.sessions.events.click({target:button});await flush();
  assert.equal(ticket,id);assert.equal(nodes['terminal-paste'].disabled,false);
  const rendered=terminal.node;
  sesiones=[{id,code:'AUX-FIXTURE',state:'active'}];await poll();
  assert(all(nodes.sessions).some(n=>n.textContent==='Asistencia en curso'));
  assert.equal(terminal.node,rendered);assert(nodes.terminal.children.includes(rendered));assert.equal(disposed,0);
  assert(!all(nodes.sessions).some(n=>n.className==='terminal-open'));
  assert(all(nodes.sessions).some(n=>n.name==='action'&&n.value==='close'));
  const trn_act=ws;
  ws.close();sesiones=[{id,code:'AUX-FIXTURE',state:'reconnecting'}];await poll();
  assert(all(nodes.sessions).some(n=>n.textContent==='Restarting / reconnecting'));
  sesiones=[{id,code:'AUX-FIXTURE',state:'ready'}];await poll();await flush();
  assert.equal(disposed,1);assert.notEqual(terminal.node,rendered);
  assert.equal(ticket,id);assert.equal(nodes['terminal-paste'].disabled,false);
  trn_act.onclose();assert.equal(nodes['terminal-paste'].disabled,false);
  sesiones=[{id,code:'<img src=x onerror=alert(1)>',state:'pending'}];await poll();
  assert(all(nodes.sessions).some(n=>n.tagName==='h3'&&n.textContent===sesiones[0].code));
  assert(!all(nodes.sessions).some(n=>n.tagName==='img'));
  sesiones=[];await poll();assert(!all(nodes.sessions).some(n=>n.tagName==='article'));
  console.log('PASS: dynamic list, safe text, retained active terminal, automatic case reconnect and stale transport isolation (Node DOM fixture)');
})().catch(err=>{console.error(err);process.exitCode=1;});
