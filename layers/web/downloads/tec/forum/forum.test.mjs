// Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
// Author & Credits: https://www.alawise.es/1-s
// Exercise visibility and moderation against real SQLite, independently of browser auth.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';
import { forumRequest } from './forum.mjs';

const dir=mkdtempSync(join(tmpdir(),'tec-forum-test-'));
const file=join(dir,'forum.sqlite');
let sqlite=new DatabaseSync(file);
for(const nom of readdirSync('drizzle').filter(n=>n.endsWith('.sql')).sort())sqlite.exec(readFileSync(join('drizzle',nom),'utf8'));
const DB={prepare(sql){
  let args=[];return {bind(...val){args=val;return this;},
    async first(){return sqlite.prepare(sql).get(...args)||null;},
    async all(){return {results:sqlite.prepare(sql).all(...args)};},
    async run(){return sqlite.prepare(sql).run(...args);}};
},async batch(items){sqlite.exec('BEGIN');try{const res=[];for(const s of items)res.push(await s.run());sqlite.exec('COMMIT');return res;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
const env={DB,FORUM_MODERATOR_EMAILS:'moderator@example.test'};
const token='a'.repeat(64);
const identity=(id,email=id+'@example.test')=>({'oai-authenticated-user-id':id,'oai-authenticated-user-email':email,'oai-authenticated-user-full-name':'Test author'});
function req(params='',id=null,data=null,extra={}) {
  const headers={...(id?identity(id,id==='admin'?'moderator@example.test':undefined):{}),...extra};
  if(data){headers.cookie='__Host-tec_csrf='+token;headers['content-type']='application/x-www-form-urlencoded';}
  return new Request('https://forum.example.test/forum'+params,{method:data?'POST':'GET',headers,body:data?new URLSearchParams({csrf:token,...data}):undefined});
}
const topic={action:'topic',name:'Author',title:'Reproducible rescue recipe',category:'recipe',evidence:'simulated',system:'Test Linux',release:'1.2.3',architecture:'x86_64',firmware:'UEFI VM',body:'<script>alert(1)</script> Procedure',commands:'printf "%s\\n" test',proof:'Simulated in an isolated virtual machine; expected result observed.',sources:'https://example.test/docs'};
try {
  let r=await forumRequest(req(),env);assert.equal(r.status,200);assert.match(r.headers.get('set-cookie'),/Secure; HttpOnly; SameSite=Strict/);
  r=await forumRequest(req('',null,topic),env);assert.equal(r.status,401);
  r=await forumRequest(req('','author',{...topic,csrf:'wrong'}),env);assert.equal(r.status,403);
  r=await forumRequest(req('','author',topic,{origin:'https://evil.example'}),env);assert.equal(r.status,403);
  r=await forumRequest(req('','author',{...topic,sources:'javascript:alert(1)'}),env);assert.equal(r.status,400);assert.match(await r.text(),/value="Reproducible rescue recipe"/);
  r=await forumRequest(req('','author',topic),env);assert.equal(r.status,303);
  const dest=r.headers.get('location');const t=sqlite.prepare('SELECT * FROM forum_topics').get();assert.equal(t.status,'pending');
  r=await forumRequest(req(dest.slice(6)),env);assert.equal(r.status,404);
  r=await forumRequest(req(dest.slice(6),'other'),env);assert.equal(r.status,404);
  r=await forumRequest(req(dest.slice(6),'author'),env);assert.equal(r.status,200);const txt=await r.text();assert.match(txt,/&lt;script&gt;/);assert.doesNotMatch(txt,/<script>/);
  r=await forumRequest(req('?moderation=1','author'),env);assert.equal(r.status,403);
  const review={action:'review',kind:'topic',id:t.id,status:'published',note:'Environment and sources reviewed; simulation recorded separately.'};
  r=await forumRequest(req('','author',review),env);assert.equal(r.status,403);
  r=await forumRequest(req('','admin',review),env);assert.equal(r.status,303);
  assert.equal(sqlite.prepare('SELECT role FROM forum_members WHERE id=?').get('admin').role,'moderator');
  r=await forumRequest(req(dest.slice(6)),env);assert.equal(r.status,200);
  r=await forumRequest(req('?export=1'),env);let json=await r.json();assert.equal(json.entries.length,1);assert.equal(json.catalog_import,'manual-review-required');assert.ok(!JSON.stringify(json).includes('@example.test'));
  r=await forumRequest(req('','other',{action:'reply',name:'Other',topic:t.id,body:'Independent test result.'}),env);assert.equal(r.status,303);
  const reply=sqlite.prepare('SELECT * FROM forum_replies').get();assert.equal(reply.status,'pending');
  r=await forumRequest(req(dest.slice(6)),env);assert.ok(!(await r.text()).includes('Independent test result.'));
  r=await forumRequest(req('','admin',{...review,kind:'reply',id:reply.id}),env);assert.equal(r.status,303);
  r=await forumRequest(req(dest.slice(6)),env);assert.ok((await r.text()).includes('Independent test result.'));
  r=await forumRequest(req('?q=%27%20OR%201%3D1--'),env);assert.equal(r.status,200);
  r=await forumRequest(req('','admin',{...review,status:'hidden'}),env);assert.equal(r.status,303);
  r=await forumRequest(req('?export=1'),env);json=await r.json();assert.equal(json.entries.length,0);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS n FROM forum_reviews').get().n,3);
  sqlite.close();sqlite=new DatabaseSync(file);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS n FROM forum_topics').get().n,1);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS n FROM forum_replies').get().n,1);
  for(const board of ['pxe','deploy','urls']){
    const res=await forumRequest(req('?board='+board),env);assert.equal(res.status,200);const page=await res.text();assert.ok(page.includes(board==='pxe'?'aux-debian-netboot-amd64':board==='deploy'?'E15':'140'));
  }
  let seed=await forumRequest(req('?board=pxe&new=1&recipe=aux-debian-netboot-amd64','author'),env);assert.match(await seed.text(),/recipe_id/);
  seed=await forumRequest(req('?board=deploy','author',{...topic,board:'deploy',category:'petition',title:'Policy contribution',recipe_id:'aux-debian-netboot-amd64',policy12:'E15'}),env);assert.equal(seed.status,303);
  const relation=sqlite.prepare("SELECT * FROM forum_topic_products WHERE board='deploy'").get();assert.equal(relation.recipe_id,'aux-debian-netboot-amd64');assert.equal(relation.policy12,'E15');
  seed=await forumRequest(req('?board=urls','author',{...topic,board:'urls',category:'petition',title:'Mirror correction',system:'',release:'',architecture:'',firmware:''}),env);assert.equal(seed.status,303);
  console.log('Forum: persistence across reopen, pending visibility, CSRF, origin, identity, XSS, bound search, replies, moderation, audit and export passed.');
}finally{sqlite.close();rmSync(dir,{recursive:true,force:true});}
