// Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
// Author and Credits: https://www.alawise.es/1-s
// Exercise the shipped workspace script with independent terminals and transport races.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const flush = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor() {this.dataset={};this.events={};this.attrs={};this.hidden=false;this.clientWidth=900;this.clientHeight=540;}
  addEventListener(nom, fn) {this.events[nom]=fn;}
  setAttribute(nom, val) {this.attrs[nom]=val;}
  focus() {this.focused=true;}
}
async function fixture(capacity=2) {
  const nodes=Object.fromEntries(['terminal-app','terminal-state',...[1,2].flatMap(idx=>
    ['tab','panel','status','paste','interrupt'].map(nom=>'terminal-'+nom+'-'+idx).concat('terminal-'+idx))].map(nom=>[nom,new Element()]));
  const id='a'.repeat(32), trms=[], sockets=[], jobs=new Map(), events={};
  nodes['terminal-app'].dataset={url:'https://cli.example.test',node:'excalibur',csrf:'fixture-csrf',session:id};
  let sesiones=[{id,state:'ready',term_cnt:capacity}], next=0, clipboard=async()=> 'K'.repeat(165), reject=false;
  class Terminal {
    constructor(cfg) {this.cols=cfg.cols;this.rows=cfg.rows;this.output='';this.decoder=new TextDecoder();trms.push(this);}
    open(el) {this.node=el;}
    onData(fn) {this.data=fn;} onBinary(fn) {this.binary=fn;} onResize(fn) {this.resizeEvent=fn;}
    write(dat, done) {this.output+=this.decoder.decode(dat,{stream:true});done?.();}
    paste(txt) {this.data(txt);} focus() {this.focused=true;}
    resize(cols, rows) {this.cols=cols;this.rows=rows;this.resizeEvent?.({cols,rows});}
    dispose() {this.disposed=true;}
  }
  class WebSocket {
    static OPEN=1;
    constructor(url) {this.url=url;this.readyState=0;this.sent=[];sockets.push(this);
      queueMicrotask(()=>{this.readyState=1;this.onopen?.();});}
    send(dat) {this.sent.push(typeof dat==='string'?dat:Uint8Array.from(dat));}
    close(code=1000) {this.readyState=3;this.code=code;this.onclose?.();}
    message(dat) {this.onmessage?.({data:typeof dat==='string'?dat:Uint8Array.from(dat).buffer});}
  }
  const context=vm.createContext({document:{getElementById:nom=>nodes[nom],createElement:()=>({getContext:()=>({measureText:()=>({width:8.4})})})},
    window:{Terminal,addEventListener:(nom,fn)=>{events[nom]=fn;}},Terminal,WebSocket,
    URLSearchParams,TextEncoder,ArrayBuffer,Uint8Array,console,navigator:{clipboard:{readText:()=>clipboard()}},
    setInterval:(fn,ms)=>{jobs.set(++next,{fn,ms});return next;},clearInterval:nom=>jobs.delete(nom),
    fetch:async(url,cfg)=>{
      assert.equal(url,'cli.php');assert.equal(cfg.body.get('csrf'),'fixture-csrf');assert.equal(cfg.body.get('id'),id);
      if(reject)return {ok:false,json:async()=>({error:'Second factor expired'})};
      return {ok:true,json:async()=>cfg.body.get('action')==='ticket'?{ticket:'fixture-ticket'}:{sessions:sesiones}};
    }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'web/terminal.js'),'utf8'),context);await flush();
  return {nodes,trms,sockets,events,jobs,
    poll:async()=>{await [...jobs.values()].find(ent=>ent.ms===5000).fn();await flush();},
    ready:()=>{sockets.at(-1).message(JSON.stringify({type:'ready',term_cnt:2}));},
    sessions:dat=>{sesiones=dat;},clipboard:fn=>{clipboard=fn;},reject:()=>{reject=true;},id};
}
function binary(ws) {return ws.sent.filter(dat=>typeof dat!=='string').map(dat=>Array.from(dat));}
(async()=>{
  const app=await fixture();assert.equal(app.trms.length,2);assert.equal(app.sockets.length,1);
  const ws=app.sockets[0];assert(ws.url.endsWith('?v=2'));
  assert.equal(app.nodes['terminal-paste-1'].disabled,true);app.ready();
  assert.equal(app.nodes['terminal-paste-1'].disabled,false);assert.equal(app.nodes['terminal-paste-2'].disabled,false);
  ws.message([1,...new TextEncoder().encode('first café')]);ws.message([2,...new TextEncoder().encode('second ñ')]);
  assert.equal(app.trms[0].output,'first café');assert.equal(app.trms[1].output,'second ñ');
  app.nodes['terminal-tab-2'].events.click();
  assert.equal(app.nodes['terminal-panel-1'].hidden,true);assert.equal(app.nodes['terminal-panel-2'].hidden,false);
  assert.equal(app.nodes['terminal-tab-2'].attrs['aria-selected'],'true');assert.equal(app.sockets.length,1);
  assert(!app.trms.some(trm=>trm.disposed));
  await app.nodes['terminal-paste-2'].events.click();
  assert.deepEqual(binary(ws).at(-1),[2,...new TextEncoder().encode('K'.repeat(165))]);
  app.nodes['terminal-interrupt-2'].events.click();assert.deepEqual(binary(ws).at(-1),[2,3]);
  const before=binary(ws).length;
  app.clipboard(async()=> 'P'.repeat(100000));await app.nodes['terminal-paste-1'].events.click();
  const paste=binary(ws).slice(before);assert.equal(paste.length,4);
  assert(paste.every(dat=>dat[0]===1&&dat.length<=32769));assert.equal(paste.reduce((n,dat)=>n+dat.length-1,0),100000);
  ws.message(JSON.stringify({type:'exit',term:1}));assert.equal(app.nodes['terminal-paste-1'].disabled,true);
  assert.equal(app.nodes['terminal-interrupt-2'].disabled,false);
  let resolve;
  app.clipboard(()=>new Promise(fn=>{resolve=fn;}));const pending=app.nodes['terminal-paste-2'].events.click();
  ws.close();await app.poll();const fresh=app.sockets.at(-1);assert.notEqual(fresh,ws);app.ready();
  resolve('must-not-reach-new-session');await pending;assert.deepEqual(binary(fresh),[]);
  ws.onclose();assert.equal(app.nodes['terminal-paste-2'].disabled,false);
  const output=app.trms[1].output;ws.message([2,88]);assert.equal(app.trms[1].output,output);
  app.reject();await [...app.jobs.values()].find(ent=>ent.ms===40000).fn();
  assert.equal(fresh.readyState,3);assert.equal(app.nodes['terminal-interrupt-1'].disabled,true);
  assert.match(app.nodes['terminal-state'].textContent,/Second factor expired/);
  app.events.pagehide();assert(app.trms.every(trm=>trm.disposed));assert.equal(app.jobs.size,0);

  const legacy=await fixture(1);assert.equal(legacy.sockets.length,0);assert.match(legacy.nodes['terminal-state'].textContent,/6.4 update/);
  legacy.events.pagehide();
  const closed=await fixture();closed.ready();closed.sessions([]);await closed.poll();
  assert.equal(closed.sockets[0].readyState,3);assert.match(closed.nodes['terminal-state'].textContent,/closed or unavailable/);
  assert.equal(closed.nodes['terminal-paste-2'].disabled,true);closed.events.pagehide();
  console.log('PASS: two retained terminals; isolated UTF-8/paste/Ctrl+C; bounded clipboard frames; independent exit; reconnect/paste races; expired authorization; legacy capability and shutdown');
})().catch(err=>{console.error(err);process.exitCode=1;});
