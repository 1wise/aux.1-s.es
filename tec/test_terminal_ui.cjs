// Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
// Author & Credits: https://www.alawise.es/1-s
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
  const id='a'.repeat(32), trms=[], sockets=[], jobs=new Map(), events={}, observers=[], frames=new Map(), fontEvents={};
  let fontsReady;
  const fonts={ready:new Promise(resolve=>{fontsReady=resolve;}),addEventListener:(nom,fn)=>{fontEvents[nom]=fn;}};
  nodes['terminal-app'].dataset={url:'https://cli.example.test',node:'excalibur',csrf:'fixture-csrf',session:id};
  let sesiones=[{id,state:'ready',term_cnt:capacity}], next=0, clipboard=async()=> 'K'.repeat(165), reject=false;
  class Terminal {
    constructor(cfg) {this.cols=cfg.cols;this.rows=cfg.rows;this.options=cfg;this.output='';this.decoder=new TextDecoder();
      this._core={_renderService:{dimensions:{css:{cell:{width:8.4,height:18}}}}};trms.push(this);}
    loadAddon(addon) {addon.activate(this);}
    open(el) {this.node=el;this.element={parentElement:el};}
    attachCustomKeyEventHandler(fn) {this.key=fn;}
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
  class ResizeObserver {constructor(fn){this.fn=fn;observers.push(this);}observe(el){this.node=el;}disconnect(){this.disconnected=true;}}
  const wind={Terminal,ResizeObserver,addEventListener:(nom,fn)=>{events[nom]=fn;},
    getComputedStyle:el=>({getPropertyValue:nom=>String(nom==='width'?el.clientWidth||0:nom==='height'?el.clientHeight||0:0)+'px'})};
  const context=vm.createContext({document:{getElementById:nom=>nodes[nom],fonts},
    window:wind,self:wind,Terminal,WebSocket,ResizeObserver,
    requestAnimationFrame:fn=>{const id=++next;frames.set(id,fn);setImmediate(()=>{if(frames.delete(id))fn();});return id;},
    cancelAnimationFrame:id=>frames.delete(id),
    URLSearchParams,TextEncoder,ArrayBuffer,Uint8Array,console,navigator:{clipboard:{readText:()=>clipboard()}},
    setInterval:(fn,ms)=>{jobs.set(++next,{fn,ms});return next;},clearInterval:nom=>jobs.delete(nom),
    fetch:async(url,cfg)=>{
      assert.equal(url,'cli.php');assert.equal(cfg.body.get('csrf'),'fixture-csrf');assert.equal(cfg.body.get('id'),id);
      if(reject)return {ok:false,json:async()=>({error:'Second factor expired'})};
      return {ok:true,json:async()=>cfg.body.get('action')==='ticket'?{ticket:'fixture-ticket'}:{sessions:sesiones}};
    }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'web/vendor/addon-fit.js'),'utf8'),context);
  wind.FitAddon=context.FitAddon||wind.FitAddon;context.FitAddon=wind.FitAddon;
  vm.runInContext(fs.readFileSync(path.join(__dirname,'web/terminal.js'),'utf8'),context);await flush();
  return {nodes,trms,sockets,events,jobs,observers,frames,fontEvents,fontsReady,
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
  app.trms[0]._core._renderService.dimensions.css.cell.width=11.2;
  app.trms[0]._core._renderService.dimensions.css.cell.height=22.5;
  app.nodes['terminal-1'].clientHeight=270;
  app.fontsReady();await flush();await flush();
  assert.equal(app.trms[0].cols,Math.floor((900-14)/11.2));assert.equal(app.trms[0].rows,12);
  assert.equal(app.trms[1].cols,100);assert.equal(app.trms[1].rows,30);
  app.nodes['terminal-1'].clientHeight=180;app.observers[0].fn();await flush();
  assert.equal(app.trms[0].rows,8);
  ws.message([1,...new TextEncoder().encode('first café')]);ws.message([2,...new TextEncoder().encode('second ñ')]);
  assert.equal(app.trms[0].output,'first café');assert.equal(app.trms[1].output,'second ñ');
  app.nodes['terminal-tab-2'].events.click();
  assert.equal(app.nodes['terminal-panel-1'].hidden,true);assert.equal(app.nodes['terminal-panel-2'].hidden,false);
  assert.equal(app.nodes['terminal-tab-2'].attrs['aria-selected'],'true');assert.equal(app.sockets.length,1);
  assert(!app.trms.some(trm=>trm.disposed));
  assert.equal(app.trms[1].cols,Math.floor((900-14)/8.4));assert.equal(app.trms[1].rows,30);
  const ev={type:'keydown',key:'PageUp',shiftKey:true,preventDefault(){this.prevented=true;}};
  assert.equal(app.trms[1].key(ev),false);assert.equal(ev.prevented,true);
  assert.deepEqual(binary(ws).at(-1),[2,...new TextEncoder().encode('\x1b[5;2~')]);
  assert.equal(app.trms[1].key({...ev,key:'PageDown'}),false);
  assert.deepEqual(binary(ws).at(-1),[2,...new TextEncoder().encode('\x1b[6;2~')]);
  const framesBefore=binary(ws).length;assert.equal(app.trms[1].key({...ev,type:'keyup'}),true);
  assert.equal(binary(ws).length,framesBefore);
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
  assert(app.observers.every(obs=>obs.disconnected));assert.equal(app.frames.size,0);

  const legacy=await fixture(1);assert.equal(legacy.sockets.length,0);assert.match(legacy.nodes['terminal-state'].textContent,/does not declare two terminals/);
  legacy.events.pagehide();
  const closed=await fixture();closed.ready();closed.sessions([]);await closed.poll();
  assert.equal(closed.sockets[0].readyState,3);assert.match(closed.nodes['terminal-state'].textContent,/closed or unavailable/);
  assert.equal(closed.nodes['terminal-paste-2'].disabled,true);closed.events.pagehide();
  console.log('PASS: real Fit addon with cell/font/resize changes; hidden tab isolation; Shift+PgUp/PgDn routing; two retained terminals, UTF-8/paste/Ctrl+C, expiry and cleanup');
})().catch(err=>{console.error(err);process.exitCode=1;});
