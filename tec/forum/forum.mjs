// Timestamp: 2026-11-17 | Version: 7.0.1-beta.4
// Author & Credits: https://www.alawise.es/1-s
// Server-rendered forms keep the community usable from Links without client scripts.
const CATEGORIAS = {recipe:"Recetas",bug:"Errores",petition:"Peticiones",solution:"Soluciones"};
const EVIDENCIAS = {tested:"Probada",simulated:"Simulada",discovery:"Descubrimiento",hypothesis:"Hipótesis"};
const ESTADOS = {pending:"Pendiente de revisión",published:"Publicada",hidden:"Retirada"};
const esc = (val="") => String(val).replace(/[&<>"']/g, x => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
const uid = () => crypto.randomUUID();
const fecha = val => new Date(val * 1000).toLocaleDateString("es-ES", {timeZone:"UTC"});
const all = async (db,sql,...args) => (await db.prepare(sql).bind(...args).all()).results;
const one = (db,sql,...args) => db.prepare(sql).bind(...args).first();
class ForumError extends Error { constructor(message,status=400){super(message);this.status=status;} }

function campo(frm,nom,max=160,required=true) {
  const txt = String(frm.get(nom) ?? "").trim();
  if ((required && !txt) || txt.length>max || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(txt)) throw new ForumError(`Revisar el campo: ${nom}.`);
  return txt;
}
function seleccion(frm,nom,opciones) {
  const val=campo(frm,nom,40);
  if (!Object.hasOwn(opciones,val)) throw new ForumError(`Opción inválida: ${nom}.`);
  return val;
}
function opciones(opc,sel) { return Object.entries(opc).map(([v,t])=>`<option value="${v}"${v===sel?" selected":""}>${t}</option>`).join(""); }
function identidad(request) {
  const id=request.headers.get("oai-authenticated-user-id");
  if (!id) return null;
  let name=request.headers.get("oai-authenticated-user-full-name") || "Colaborador";
  if (request.headers.get("oai-authenticated-user-full-name-encoding")==="percent-encoded-utf-8") {
    try { name=decodeURIComponent(name); } catch { name="Colaborador"; }
  }
  return {id,email:request.headers.get("oai-authenticated-user-email") || "",name:name.slice(0,80)};
}
function csrf(request) {
  return request.headers.get("cookie")?.match(/(?:^|;\s*)__Host-tec_csrf=([a-f0-9]{64})(?:;|$)/)?.[1];
}
function nuevoToken() { return Array.from(crypto.getRandomValues(new Uint8Array(32)),v=>v.toString(16).padStart(2,"0")).join(""); }
function ocultos(act,ctx,extra={}) {
  return `<input type="hidden" name="action" value="${act}"><input type="hidden" name="csrf" value="${ctx.token}">`+
    Object.entries(extra).map(([k,v])=>`<input type="hidden" name="${k}" value="${esc(v)}">`).join("");
}
function ruta(ctx,params={}) {
  const par=new URLSearchParams(params); if(ctx.pxe)par.set("view","pxe");
  return "/forum"+(par.size?"?"+par.toString():"");
}
function enlace(ctx,params,text,cls="") { return `<a class="${cls}" href="${esc(ruta(ctx,params))}">${text}</a>`; }
function formulario(ctx,act,body,extra={}) {
  return `<form method="post" action="${esc(ruta(ctx))}">${ocultos(act,ctx,extra)}${body}</form>`;
}
function autor(ctx,nom=null) { return `<label>Nombre público<input name="name" maxlength="80" required value="${esc(nom ?? ctx.member?.name ?? ctx.user?.name)}"><small>Firma visible en el foro. El correo de la cuenta no se publica.</small></label>`; }
function ficha(ctx,t) {
  return `<article class="topic-card"><div class="topic-mark">${esc(CATEGORIAS[t.category])}</div><div><div class="badges"><span>${esc(EVIDENCIAS[t.evidence])}</span>${t.status!=="published"?`<span class="pending">${ESTADOS[t.status]}</span>`:""}</div><h2>${enlace(ctx,{topic:t.slug},esc(t.title))}</h2><p>${esc(t.system)} · ${esc(t.release)} · ${esc(t.architecture)} · ${esc(t.firmware)}</p><small>${esc(t.name)} · ${fecha(t.updated)}</small></div><span class="topic-arrow">↗</span></article>`;
}
function reglas() {
  return `<details class="guidelines"><summary>Cómo aportar una receta útil</summary><p>Indicar sistema, versión exacta, arquitectura y firmware; explicar el objetivo, los pasos, el resultado esperado y las fuentes.</p><p>Probada: prueba real y resultado. Simulada: entorno de simulación. Descubrimiento: observación documentada. Hipótesis: propuesta pendiente de contrastar.</p><p>Las aportaciones se revisan antes de publicarse. La revisión editorial y las pruebas de arranque se registran por separado. Las recetas publicadas se incorporan al catálogo mediante su proceso de validación.</p></details>`;
}
function pagina(ctx,titulo,cuerpo,status=200) {
  const nav = `<nav aria-label="Navegación TEC"><a href="/index.html">Volver a ./aux</a><a href="/index-pxe.html">PXE · ISO</a><a href="/pxe/commands.html">Guías de comandos</a>${enlace(ctx,{},"Foro de recetas")}${enlace({...ctx,pxe:!ctx.pxe},{},ctx.pxe?"Vista gráfica":"Vista Links")}${ctx.moderator?enlace(ctx,{moderation:"1"},"Moderación"):""}</nav>`;
  const html=`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Foro TEC: recetas, errores, peticiones y soluciones de sistemas y netboot."><title>${esc(titulo)} · tec.*</title><link rel="icon" href="/assets/favicon.png"><link rel="stylesheet" href="/forum.css"></head><body class="${ctx.pxe?"pxe":"aux"}"><a class="skip" href="#content">Ir al contenido</a><header><div class="identity"><a class="tec-logo" href="/forum">tec.*</a><span>RECETAS / COMUNIDAD</span><small>AUX 7.0.1-beta.4</small></div>${nav}</header><main id="content">${cuerpo}</main><footer><a href="https://www.alawise.es/1-s">1wise · Conocimiento compartido</a><span>./aux · PXE&gt;_ · tec.*</span><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a></footer></body></html>`;
  const headers={"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"same-origin","Content-Security-Policy":"default-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"};
  if(ctx.setCookie)headers["Set-Cookie"]=`__Host-tec_csrf=${ctx.token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=7200`;
  return new Response(html,{status,headers});
}
function formularioTema(ctx,frm=new URLSearchParams(),err="") {
  const field=(nom,label,max=160,hint="")=>`<label>${label}<input name="${nom}" maxlength="${max}" required value="${esc(frm.get(nom)||"")}">${hint?`<small>${hint}</small>`:""}</label>`;
  const area=(nom,label,max,hint,req=true)=>`<label>${label}<textarea name="${nom}" maxlength="${max}" rows="${nom==="commands"?8:5}" ${req?"required":""}>${esc(frm.get(nom)||"")}</textarea><small>${hint}</small></label>`;
  return `<section class="page-intro"><p class="eyebrow">APORTAR / REVISAR / COMPARTIR</p><h1>Una receta que permita repetir el resultado.</h1><p>La aportación queda en revisión. Los campos conservan su contenido si falta algún dato.</p></section>${err?`<p class="notice" role="alert">${esc(err)}</p>`:""}${formulario(ctx,"topic",`<div class="form-grid"><section class="panel">${autor(ctx,frm.get("name"))}${field("title","Título",160)}<div class="two"><label>Tipo<select name="category">${opciones(CATEGORIAS,frm.get("category")||"recipe")}</select></label><label>Evidencia<select name="evidence">${opciones(EVIDENCIAS,frm.get("evidence")||"hypothesis")}</select></label></div>${field("system","Sistema o distribución",80,"Ejemplo: Debian, Fedora, Alpine o una herramienta de rescate.")}${field("release","Versión exacta",80)}<div class="two">${field("architecture","Arquitectura",40)}${field("firmware","Firmware / entorno",60,"BIOS, UEFI, máquina virtual u otro entorno.")}</div></section><section class="panel">${area("body","Objetivo y procedimiento",12000,"Explicar el punto de partida y el resultado esperado.")}${area("commands","Comandos o receta",12000,"Texto literal. Se publica para lectura y revisión; no se ejecuta desde el foro.",false)}${area("proof","Prueba, resultado y límites",6000,"Para Probada o Simulada, describir el entorno y el resultado observado.")}${area("sources","Fuentes",2000,"Una URL http/https por línea; hasta diez referencias.",false)}</section></div><div class="actions"><button type="submit">Enviar a revisión</button>${enlace(ctx,{},"Volver al foro","button secondary")}</div><p class="form-note">Las aportaciones se comparten bajo CC BY-NC-SA 4.0.</p>`)}${reglas()}`;
}
async function lista(ctx,par) {
  const q=(par.get("q")||"").slice(0,100),cat=par.get("category")||"",evi=par.get("evidence")||"";
  const page=Math.max(0,Math.min(10000,Number.parseInt(par.get("page")||"0",10)||0));
  let where="t.status = 'published'",args=[];
  if(ctx.user){where="(t.status = 'published' OR t.author = ?"+(ctx.moderator?" OR 1=1":"")+")";args.push(ctx.user.id);}
  if(cat && Object.hasOwn(CATEGORIAS,cat)){where+=" AND t.category=?";args.push(cat);}
  if(evi && Object.hasOwn(EVIDENCIAS,evi)){where+=" AND t.evidence=?";args.push(evi);}
  if(q){where+=" AND (t.title LIKE ? ESCAPE '\\' OR t.body LIKE ? ESCAPE '\\')";const s="%"+q.replace(/[\\%_]/g,"\\$&")+"%";args.push(s,s);}
  const temas=await all(ctx.db,`SELECT t.*,m.name FROM forum_topics t JOIN forum_members m ON m.id=t.author WHERE ${where} ORDER BY t.updated DESC,t.id LIMIT 21 OFFSET ?`,...args,page*20);
  return `<section class="page-intro"><p class="eyebrow">TEC / CONOCIMIENTO QUE SE PUEDE REPRODUCIR</p><h1>Probar. Documentar.<br><em>Compartir la receta.</em></h1><p>Netboot, instalación y rescate. Un lugar para contrastar procedimientos, resolver errores y convertir hallazgos en recetas útiles.</p><div class="actions">${ctx.user?enlace(ctx,{new:"1"},"+ Nueva aportación","button"):enlace(ctx,{login:"1"},"Entrar para aportar","button")}${enlace(ctx,{export:"1"},"Exportar recetas publicadas · JSON","text-link")}</div></section><div class="community-bar"><span>Recetas</span><span>Errores</span><span>Peticiones</span><span>Soluciones</span></div><form method="get" action="/forum" class="filters">${ctx.pxe?'<input type="hidden" name="view" value="pxe">':""}<label>Buscar<input name="q" value="${esc(q)}" maxlength="100" placeholder="Sistema, problema o procedimiento"></label><label>Tipo<select name="category"><option value="">Todos</option>${opciones(CATEGORIAS,cat)}</select></label><label>Evidencia<select name="evidence"><option value="">Todas</option>${opciones(EVIDENCIAS,evi)}</select></label><button>Filtrar</button></form><section aria-label="Aportaciones">${temas.length?temas.slice(0,20).map(t=>ficha(ctx,t)).join(""):`<div class="empty"><span>./</span><h2>${q||cat||evi?"Sin coincidencias":"La primera receta abre camino."}</h2><p>${q||cat||evi?"Cambiar los filtros para ampliar la búsqueda.":"El foro está preparado para recibir recetas y preguntas. Cada aportación conserva su evidencia y su revisión."}</p>${ctx.user?enlace(ctx,{new:"1"},"Preparar una aportación","button secondary"):""}</div>`}</section><div class="pagination">${page?enlace(ctx,{q,category:cat,evidence:evi,page:String(page-1)},"← Anteriores"):""}${temas.length>20?enlace(ctx,{q,category:cat,evidence:evi,page:String(page+1)},"Siguientes →"):""}</div>${reglas()}`;
}
function revision(ctx,kind,id) {
  return formulario(ctx,"review",`<label>Decisión<select name="status"><option value="published">Publicar</option><option value="pending">Devolver a revisión</option><option value="hidden">Retirar</option></select></label><label>Motivo o comprobaciones<textarea name="note" maxlength="2000" required rows="3"></textarea></label><button>Guardar revisión</button>`,{kind,id});
}
async function tema(ctx,slug,par,frm=new URLSearchParams(),err="") {
  const t=await one(ctx.db,"SELECT t.*,m.name FROM forum_topics t JOIN forum_members m ON m.id=t.author WHERE t.slug=?",slug);
  if(!t || (t.status!=="published" && !ctx.moderator && ctx.user?.id!==t.author))throw new ForumError("Tema no encontrado.",404);
  const pag=Math.max(0,Math.min(10000,Number.parseInt(par.get("replies")||"0",10)||0));
  const respuestas=await all(ctx.db,"SELECT r.*,m.name FROM forum_replies r JOIN forum_members m ON m.id=r.author WHERE r.topic=? AND (r.status='published' OR r.author=? OR ?=1) ORDER BY r.created,r.id LIMIT 51 OFFSET ?",t.id,ctx.user?.id||"",ctx.moderator?1:0,pag*50);
  const revisiones=await all(ctx.db,"SELECT r.*,m.name FROM forum_reviews r JOIN forum_members m ON m.id=r.moderator WHERE r.target=? ORDER BY r.created DESC LIMIT 10",t.id);
  const code=t.commands?`<h2>Comandos / receta</h2><pre><code>${esc(t.commands)}</code></pre>`:"";
  const refs=t.sources.split("\n").filter(Boolean).map(url=>`<li><a href="${esc(url)}" rel="nofollow noopener">${esc(url)}</a></li>`).join("");
  return `<section class="page-intro"><p class="eyebrow">${CATEGORIAS[t.category]} / ${EVIDENCIAS[t.evidence]}</p><h1>${esc(t.title)}</h1><p>${esc(t.name)} · ${fecha(t.created)} · ${ESTADOS[t.status]}</p></section><dl class="environment"><div><dt>Sistema</dt><dd>${esc(t.system)}</dd></div><div><dt>Versión</dt><dd>${esc(t.release)}</dd></div><div><dt>Arquitectura</dt><dd>${esc(t.architecture)}</dd></div><div><dt>Firmware</dt><dd>${esc(t.firmware)}</dd></div></dl><article class="panel"><h2>Objetivo y procedimiento</h2><div class="prose">${esc(t.body)}</div>${code}<h2>Prueba y resultado declarado</h2><div class="prose">${esc(t.proof)}</div>${refs?`<h2>Fuentes</h2><ul>${refs}</ul>`:""}</article>${revisiones.length?`<section class="review-log"><h2>Historial de revisión editorial</h2>${revisiones.map(r=>`<p>${fecha(r.created)} · ${esc(r.name)} · ${ESTADOS[r.action]}<br>${esc(r.note)}</p>`).join("")}</section>`:""}${ctx.moderator?`<details class="panel"><summary>Revisar esta aportación</summary>${revision(ctx,"topic",t.id)}</details>`:""}<section class="responses"><h2>Contrastar la receta</h2>${respuestas.slice(0,50).map(r=>`<article class="panel reply"><p><strong>${esc(r.name)}</strong> · ${fecha(r.created)} · ${ESTADOS[r.status]}</p><div class="prose">${esc(r.body)}</div>${ctx.moderator?`<details><summary>Revisar respuesta</summary>${revision(ctx,"reply",r.id)}</details>`:""}</article>`).join("")}${pag?enlace(ctx,{topic:slug,replies:String(pag-1)},"← Respuestas anteriores"):""}${respuestas.length>50?enlace(ctx,{topic:slug,replies:String(pag+1)},"Más respuestas →"):""}${err?`<p class="notice" role="alert">${esc(err)}</p>`:""}${ctx.user?formulario(ctx,"reply",`${autor(ctx,frm.get("name"))}<label>Respuesta<textarea name="body" maxlength="8000" required rows="6">${esc(frm.get("body")||"")}</textarea><small>Describir la prueba, la corrección o la pregunta. La respuesta pasa por revisión.</small></label><button>Enviar respuesta a revisión</button>`,{topic:t.id}):'<p><a href="/signin-with-chatgpt?return_to=%2Fforum" target="_top">Entrar para responder</a></p>'}</section>`;
}
async function moderacion(ctx) {
  if(!ctx.moderator)throw new ForumError("Acceso reservado a moderación.",403);
  const temas=await all(ctx.db,"SELECT t.*,m.name FROM forum_topics t JOIN forum_members m ON m.id=t.author WHERE t.status='pending' ORDER BY t.created LIMIT 100");
  const respuestas=await all(ctx.db,"SELECT r.*,m.name,t.slug,t.title FROM forum_replies r JOIN forum_members m ON m.id=r.author JOIN forum_topics t ON t.id=r.topic WHERE r.status='pending' ORDER BY r.created LIMIT 100");
  return `<section class="page-intro"><p class="eyebrow">TEC / REVISIÓN EDITORIAL</p><h1>Contrastar antes de compartir.</h1><p>Revisar el entorno, las fuentes y la evidencia declarada. Aprobar aquí no añade un lanzador al catálogo.</p></section><h2>Temas pendientes</h2>${temas.length?temas.map(t=>ficha(ctx,t)).join(""):'<p class="empty-small">No hay temas pendientes.</p>'}<h2>Respuestas pendientes</h2>${respuestas.length?respuestas.map(r=>`<article class="panel"><h3>${enlace(ctx,{topic:r.slug},esc(r.title))}</h3><p>${esc(r.name)}</p><div class="prose">${esc(r.body)}</div>${revision(ctx,"reply",r.id)}</article>`).join(""):'<p class="empty-small">No hay respuestas pendientes.</p>'}${reglas()}`;
}
async function leeFormulario(request) {
  if(!request.headers.get("content-type")?.startsWith("application/x-www-form-urlencoded"))throw new ForumError("Formato de formulario no admitido.",415);
  const reader=request.body?.getReader();let bytes=0,parts=[];
  if(!reader)throw new ForumError("Formulario vacío.");
  for(;;){const {value,done}=await reader.read();if(done)break;bytes+=value.length;if(bytes>65536){await reader.cancel();throw new ForumError("Formulario demasiado grande.",413);}parts.push(value);}
  const buf=new Uint8Array(bytes);let off=0;for(const p of parts){buf.set(p,off);off+=p.length;}
  return new URLSearchParams(new TextDecoder().decode(buf));
}
async function guarda(ctx,frm) {
  if(!ctx.user)throw new ForumError("Iniciar sesión para aportar.",401);
  const now=Math.floor(Date.now()/1000),act=campo(frm,"action",20);
  const recientes=await one(ctx.db,"SELECT (SELECT COUNT(*) FROM forum_topics WHERE author=? AND created>?)+(SELECT COUNT(*) FROM forum_replies WHERE author=? AND created>?) AS n",ctx.user.id,now-600,ctx.user.id,now-600);
  if(recientes.n>=30)throw new ForumError("Límite temporal de aportaciones alcanzado. Esperar unos minutos.",429);
  const nom=act==="review"?(ctx.member?.name||ctx.user.name):campo(frm,"name",80);
  const miembro=ctx.db.prepare("INSERT INTO forum_members(id,name,role,created) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name").bind(ctx.user.id,nom,ctx.moderator?"moderator":"member",now);
  if(act==="topic") {
    const title=campo(frm,"title"),category=seleccion(frm,"category",CATEGORIAS),evidence=seleccion(frm,"evidence",EVIDENCIAS);
    const body=campo(frm,"body",12000),commands=campo(frm,"commands",12000,false),proof=campo(frm,"proof",6000);
    if((category==="recipe"||category==="solution")&&!commands)throw new ForumError("La receta o solución necesita sus comandos o pasos reproducibles.");
    if((evidence==="tested"||evidence==="simulated")&&proof.length<20)throw new ForumError("Describir el entorno de prueba y el resultado observado con más detalle.");
    const sources=campo(frm,"sources",2000,false).split(/\r?\n/).filter(Boolean).map(s=>s.trim());
    if(sources.length>10)throw new ForumError("Usar hasta diez fuentes.");
    for(const s of sources){let u;try{u=new URL(s);}catch{throw new ForumError("Revisar la URL de una fuente.");}if(!["http:","https:"].includes(u.protocol)||u.username||u.password)throw new ForumError("Las fuentes requieren URL http/https sin credenciales.");}
    const id=uid(),slug=title.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,90)+"-"+id.slice(0,8);
    await ctx.db.batch([miembro,ctx.db.prepare("INSERT INTO forum_topics(id,slug,title,category,evidence,system,release,architecture,firmware,body,commands,proof,sources,author,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending',?,?)").bind(id,slug,title,category,evidence,campo(frm,"system",80),campo(frm,"release",80),campo(frm,"architecture",40),campo(frm,"firmware",60),body,commands,proof,sources.join("\n"),ctx.user.id,now,now)]);
    return ruta(ctx,{topic:slug});
  }
  if(act==="reply") {
    const t=await one(ctx.db,"SELECT * FROM forum_topics WHERE id=?",campo(frm,"topic",40));
    if(!t||(t.status!=="published"&&!ctx.moderator&&ctx.user.id!==t.author))throw new ForumError("Tema no encontrado.",404);
    await ctx.db.batch([miembro,ctx.db.prepare("INSERT INTO forum_replies(id,topic,author,body,status,created) VALUES(?,?,?,?,'pending',?)").bind(uid(),t.id,ctx.user.id,campo(frm,"body",8000),now)]);
    return ruta(ctx,{topic:t.slug});
  }
  if(act==="review") {
    if(!ctx.moderator)throw new ForumError("Acceso reservado a moderación.",403);
    const kind=seleccion(frm,"kind",{topic:1,reply:1}),id=campo(frm,"id",40),status=seleccion(frm,"status",ESTADOS),note=campo(frm,"note",2000);
    const table=kind==="topic"?"forum_topics":"forum_replies";
    const target=await one(ctx.db,`SELECT * FROM ${table} WHERE id=?`,id);
    if(!target)throw new ForumError("Aportación no encontrada.",404);
    const t=kind==="topic"?target:await one(ctx.db,"SELECT * FROM forum_topics WHERE id=?",target.topic);
    if(kind==="reply"&&status==="published"&&t.status!=="published")throw new ForumError("Publicar el tema antes de publicar sus respuestas.");
    await ctx.db.batch([miembro,ctx.db.prepare(`UPDATE ${table} SET status=?${kind==="topic"?",updated=?":""} WHERE id=?`).bind(...(kind==="topic"?[status,now,id]:[status,id])),ctx.db.prepare("INSERT INTO forum_reviews(id,target,kind,action,note,moderator,created) VALUES(?,?,?,?,?,?,?)").bind(uid(),id,kind,status,note,ctx.user.id,now)]);
    return ruta(ctx,{topic:t.slug});
  }
  throw new ForumError("Acción no admitida.");
}

export async function forumRequest(request,env) {
  const url=new URL(request.url),user=identidad(request),cookie=csrf(request);
  const ctx={user,db:env.DB,token:cookie||nuevoToken(),setCookie:!cookie,pxe:url.searchParams.get("view")==="pxe",member:null,moderator:false};
  let frm;
  try {
    if(!ctx.db)throw new ForumError("El foro necesita su almacenamiento persistente.",503);
    if(user){ctx.member=await one(ctx.db,"SELECT * FROM forum_members WHERE id=?",user.id);ctx.moderator=ctx.member?.role==="moderator"||(!ctx.member&&String(env.FORUM_MODERATOR_EMAILS||"").split(",").map(s=>s.trim().toLowerCase()).includes(user.email.toLowerCase())&&!!user.email);}
    if(request.method==="POST") {
      const origin=request.headers.get("origin");
      if((origin&&origin!==url.origin)||request.headers.get("sec-fetch-site")==="cross-site")throw new ForumError("Origen del formulario no permitido.",403);
      frm=await leeFormulario(request);
      if(!cookie||frm.get("csrf")!==cookie)throw new ForumError("Formulario caducado. Recargar antes de enviar.",403);
      const dest=await guarda(ctx,frm);
      return new Response(null,{status:303,headers:{Location:dest,"Cache-Control":"no-store"}});
    }
    if(url.searchParams.has("login"))return new Response(null,{status:303,headers:{Location:"/signin-with-chatgpt?return_to=%2Fforum"}});
    if(url.searchParams.has("export")) {
      const entries=await all(ctx.db,"SELECT t.slug,t.title,t.category,t.evidence,t.system,t.release,t.architecture,t.firmware,t.body,t.commands,t.proof,t.sources,t.created,t.updated,m.name AS author FROM forum_topics t JOIN forum_members m ON m.id=t.author WHERE t.status='published' ORDER BY t.updated DESC LIMIT 1000");
      return new Response(JSON.stringify({schema:"tec-forum-recipes-v1",catalog_import:"manual-review-required",entries},null,2),{headers:{"Content-Type":"application/json; charset=utf-8","Content-Disposition":"attachment; filename=tec-recipes.json","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
    }
    if(url.searchParams.has("new")) {
      if(!user)throw new ForumError("Iniciar sesión para aportar.",401);
      return pagina(ctx,"Nueva aportación",formularioTema(ctx));
    }
    if(url.searchParams.has("moderation"))return pagina(ctx,"Moderación",await moderacion(ctx));
    if(url.searchParams.has("topic"))return pagina(ctx,"Receta",await tema(ctx,url.searchParams.get("topic"),url.searchParams));
    return pagina(ctx,"Foro de recetas",await lista(ctx,url.searchParams));
  } catch(err) {
    if(!(err instanceof ForumError)){console.error("TEC forum request failed",err.message);return pagina(ctx,"Foro no disponible",'<h1>El foro no está disponible.</h1><p>Revisar el almacenamiento y las migraciones del servicio.</p>',503);}
    if(frm?.get("action")==="topic"&&err.status===400)return pagina(ctx,"Revisar aportación",formularioTema(ctx,frm,err.message),400);
    if(frm?.get("action")==="reply"&&err.status===400) {
      const t=await one(ctx.db,"SELECT slug FROM forum_topics WHERE id=?",frm.get("topic")||"");
      if(t)return pagina(ctx,"Revisar respuesta",await tema(ctx,t.slug,url.searchParams,frm,err.message),400);
    }
    return pagina(ctx,"Revisar operación",`<h1>${esc(err.message)}</h1><p>${enlace(ctx,{},"Volver al foro")}</p>`,err.status);
  }
}
