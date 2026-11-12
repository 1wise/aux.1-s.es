/** Timestamp: 2026-11-10 | Version: 7.0.0-beta.19 | Author & Credits: https://www.alawise.es/1-s */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
class Nodo {
  constructor(tag='div'){this.tag=tag;this.children=[];this.attributes={};this.textContent='';this.value='';}
  get childNodes(){return this.children;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(key,val){this.attributes[key]=val;}
  removeAttribute(key){delete this.attributes[key];}
  addEventListener(){}
}
const local={id:'local',name:'Local Linux',filename:'linux.iso',family:'debian',arch:'x86_64',release:'1',format:'ISO',category:'distribution',url:'https://example.org/linux.iso',published:true,download_urls:{source:'https://example.org/linux.iso',excalibur:'http://pxe.example.org/linux.iso'}};
const origen={id:'origin',name:'TinyOS',filename:'tiny.ipxe',family:'tinyos',arch:'upstream',release:'rolling',format:'MENU',category:'distribution',url:'https://boot.netboot.xyz/tiny.ipxe',origin_only:true,origin_launcher:'origins/tiny.ipxe',published:false,download_urls:{source:'https://boot.netboot.xyz/tiny.ipxe'}};
const dat={resources:[local],origin_resources:[origen],hierarchy:[{id:'tiny',category:'distribution',resources:['origin'],children:[]}]};
const elems={'catalog-data':{textContent:JSON.stringify(dat)},search:{value:''},arch:{value:'all'},sort:{value:'catalog'},mirror:{value:'bastion'}};
const document={getElementById:nom=>elems[nom]||(elems[nom]=new Nodo()),createElement:tag=>new Nodo(tag),createTextNode:text=>String(text),querySelectorAll:()=>[]};
const ctx=vm.createContext({document,console,URL,setTimeout,clearTimeout});
const src=fs.readFileSync(path.resolve(__dirname,'../src/portal.js'),'utf8').split("el('search').addEventListener")[0];
vm.runInContext(src,ctx);
assert.equal(vm.runInContext('flt_rec().length',ctx),2);
vm.runInContext("flt_nod='tiny';flt_cat='distribution'",ctx);
assert.equal(vm.runInContext('flt_rec()[0].id',ctx),'origin');
assert.equal(vm.runInContext('obt_url(rec_all[1])',ctx),origen.url);
const row=vm.runInContext('gen_row(rec_all[1])',ctx);
function todos(nodo){return typeof nodo==='string'?[]:[nodo,...nodo.children.flatMap(todos)];}
const enlaces=todos(row).filter(n=>n.tag==='a');
assert(enlaces.some(n=>n.href===origen.origin_launcher&&n.textContent==='iPXE'));
assert(enlaces.some(n=>n.href===origen.url));
assert(!enlaces.some(n=>String(n.href).includes('bastion')));
vm.runInContext('act_rec(rec_all[1])',ctx);
assert.equal(elems['resource-url'].value,origen.url);
assert.equal(elems['resource-contents'].hidden,true);
console.log('Origin UI: combined inventory, unknown family, provider routing, iPXE link and no invented local contents passed.');
