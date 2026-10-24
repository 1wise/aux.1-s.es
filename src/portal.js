/** Timestamp: 2026-10-13 | Version: 5.0.7 | Author & Credits: https://www.alawise.es/1-s */
'use strict';

const dat_cat = JSON.parse(document.getElementById('catalog-data').textContent);
const rec_all = dat_cat.resources || [];
const el = nom_id => document.getElementById(nom_id);
let flt_cat = 'all';
let flt_nod = '';
const arbol_cat = dat_cat.hierarchy || [];
const nodos_cat = new Map();
function registra_nodos(nodos) {
  for (const nodo of nodos) {nodos_cat.set(nodo.id,nodo);registra_nodos(nodo.children);}
}
registra_nodos(arbol_cat);
function obt_ids(nodo) {return [...nodo.resources,...nodo.children.flatMap(obt_ids)];}
let mod_act = 'ram';
let rec_act = null;
let tmr_toast;
const sym_fam = {debian:'◉', fedora:'f', ubuntu:'◌', arch:'A', gentoo:'g', kali:'K', proxmox:'×', clonezilla:'C', gparted:'▥', memtest:'▤', netboot:'↗', dban:'D', supergrub:'S', bootrepair:'↻'};
const url_pxe = dat_cat.pxe_url || 'http://pxe.1-s.es';
const cmd_boot = `dhcp\nchain ${url_pxe}/menu.ipxe`;
const mod_desc = {
  disk:['Heavy list / persistent disk', 'Select heavy-url.txt for desktop Live images, full installers and Arch ISOs. Copy the cached files and extract their contents into persistent directories. RAM and disk share the catalog.'],
  ram:['Light list / RAM', 'Select light-url.txt for netinstall, minimal Gentoo and tools. Copy cached files into tmpfs and publish their contents through symlinks. Check free memory first.'],
  ftp:['FTP / Bastion replica', 'Upload the prepared html contents and cached ISOs to one FTP root. Prepare and generate locally first. The password is requested privately; FTPS is the default.']
};

// Server choice affects complete downloads only; boot and image contents stay on Excalibur.
const url_bastion = dat_cat.download_url || 'https://b.1-s.es';
const srv_labels = {bastion:'Bastion · France',excalibur:'Excalibur · Canada',source:'Original URL'};
function obt_downloads(rec) {
  if (rec.format === 'TREE') return {};
  if (rec.download_urls) return rec.download_urls;
  if (['checksum-failed','invalid-payload'].includes(rec.status)) return {source:rec.url};
  const path = (rec.path || rec.filename).split('/').map(encodeURIComponent).join('/');
  const urls = {bastion:`${url_bastion.replace(/\/$/, '')}/${path}`};
  if (rec.published || rec.status === 'source') urls.excalibur=`${url_pxe.replace(/\/$/, '')}/${path}`;
  urls.source=rec.url;
  return urls;
}
function obt_url(rec) {
  if (rec.format === 'TREE') return obt_contents_url(rec) || `${url_pxe.replace(/\/$/, '')}/${(rec.path || rec.tree).split('/').map(encodeURIComponent).join('/')}/`;
  const urls=obt_downloads(rec);
  return urls[el('mirror').value] || urls.bastion || urls.source;
}
function obt_contents_url(rec) {
  if (!rec.contents_ready || !rec.published || ['checksum-failed','invalid-payload'].includes(rec.status)) return null;
  return rec.contents_path || `contents/${rec.id}/index.html`;
}
function gen_servers(rec) {
  const links=document.createElement('span');
  links.className='server-links';
  for (const [key,url] of Object.entries(obt_downloads(rec))) {
    if (links.childNodes.length) links.append(document.createTextNode(' | '));
    const link=document.createElement('a');link.href=url;link.textContent=srv_labels[key];links.append(link);
  }
  return links;
}

function flt_rec() {
  const bus_txt = el('search').value.toLowerCase().trim();
  const arq_act = el('arch').value;
  const ids = flt_nod && nodos_cat.has(flt_nod) ? new Set(obt_ids(nodos_cat.get(flt_nod))) : null;
  let rec_vis = rec_all.filter(rec =>
    (!ids || ids.has(rec.id)) &&
    (flt_cat === 'all' || rec.category === flt_cat) &&
    (arq_act === 'all' || rec.arch === arq_act) &&
    [rec.name,rec.filename,rec.release,rec.family,rec.arch].join(' ').toLowerCase().includes(bus_txt));
  if (el('sort').value === 'name') rec_vis.sort((a,b) => a.name.localeCompare(b.name) || a.filename.localeCompare(b.filename));
  if (el('sort').value === 'release') rec_vis.sort((a,b) => b.release.localeCompare(a.release,undefined,{numeric:true}) || a.name.localeCompare(b.name));
  return rec_vis;
}

function gen_row(rec) {
  const fil = document.createElement('tr');
  const cel_nom = document.createElement('td');
  const div_nom = document.createElement('div');
  div_nom.className = 'resource-cell';
  const ico = document.createElement('span');
  ico.className = `distro-icon ${rec.family}`;
  ico.textContent = sym_fam[rec.family] || '↗';
  ico.setAttribute('aria-hidden','true');
  const div_txt = document.createElement('div');
  const btn_nom = document.createElement('a');
  btn_nom.className = 'resource-name';
  btn_nom.href = `files/${rec.id}.html`;
  btn_nom.textContent = rec.name;
  btn_nom.addEventListener('click',evt => open_details(evt,rec));
  const arc_nom = document.createElement('span');
  arc_nom.className = 'resource-filename';
  arc_nom.textContent = rec.filename;
  arc_nom.title = rec.filename;
  div_txt.append(btn_nom,arc_nom);
  const url_tree = obt_contents_url(rec);
  if (url_tree) {
    const nav_tree = document.createElement('a');
    nav_tree.className = 'contents-link';
    nav_tree.href = url_tree;
    nav_tree.textContent = 'Browse files · Excalibur';
    div_txt.append(nav_tree);
  }
  div_nom.append(ico,div_txt);
  cel_nom.append(div_nom);
  fil.append(cel_nom);
  for (const [val,cls] of [[rec.release,'release'],[rec.arch === 'arm64' ? 'ARM64' : rec.arch,'arch-badge'],[rec.format,'format-badge']]) {
    const cel = document.createElement('td');
    const spn = document.createElement('span');
    spn.className = cls;
    spn.textContent = val;
    cel.append(spn);
    if (cls === 'format-badge') {
      const kind=document.createElement('small');kind.className='media-kind';
      kind.textContent=(rec.kind || 'tool').replace(/^./,c=>c.toUpperCase());cel.append(kind);
    }
    fil.append(cel);
  }
  const cel_acc = document.createElement('td');
  const div_acc = document.createElement('div');
  div_acc.className = 'row-actions';
  const lnk = document.createElement('a');
  lnk.className = 'download-link';
  lnk.href = obt_url(rec);
  lnk.target = '_blank';
  lnk.rel = 'noopener noreferrer';
  lnk.setAttribute('aria-label',`Download ${rec.name}, ${rec.arch}`);
  lnk.append(document.createTextNode(rec.format === 'TREE' ? 'Browse files ' : 'Download '));
  const fle = document.createElement('span');
  fle.textContent = '↓';
  fle.setAttribute('aria-hidden','true');
  lnk.append(fle);
  const btn = document.createElement('a');
  btn.className = 'details-button';
  btn.href = `files/${rec.id}.html`;
  btn.textContent = '⋯';
  btn.setAttribute('aria-label',`Details for ${rec.name}`);
  btn.addEventListener('click',evt => open_details(evt,rec));
  div_acc.append(lnk,btn);
  cel_acc.append(div_acc,gen_servers(rec));
  fil.append(cel_acc);
  return fil;
}

function act_cat() {
  const rec_vis = flt_rec();
  const rows=[];
  const ids_vis=new Set(rec_vis.map(rec=>rec.id));
  let asistencia_vacia=false;
  function visita(nodos,nivel=0) {
    for (const nodo of nodos) {
      const vacio=nodo.id==='nav_assistance' && !nodo.resources.length &&
        ['all','assistance'].includes(flt_cat) && !el('search').value.trim() && el('arch').value==='all';
      if (!vacio && !obt_ids(nodo).some(id=>ids_vis.has(id))) continue;
      const head=document.createElement('tr');head.className=`category-heading tree-level-${nivel}`;head.id=nodo.id;
      const title=document.createElement('th');title.colSpan=5;title.scope='colgroup';
      title.textContent=`${nodo.number}. ${nodo.label}`;
      head.append(title);rows.push(head);
      if(vacio) {
        asistencia_vacia=true;
        const row=document.createElement('tr'),cell=document.createElement('td');cell.colSpan=5;
        cell.append('No assistance ISO deployed yet. ');
        if (dat_cat.tec_enabled !== false) {
          const link=document.createElement('a');link.href=(document.body.dataset.tecUrl || 'https://tec.1-s.es') + '/';link.textContent='Choose a technician';
          cell.append(link);
        }
        row.append(cell);rows.push(row);
      }
      visita(nodo.children,nivel+1);
      const ids=new Set(nodo.resources);
      rows.push(...rec_vis.filter(rec=>ids.has(rec.id)).map(gen_row));
    }
  }
  if (arbol_cat.length) visita(arbol_cat);
  else rows.push(...rec_vis.map(gen_row));
  el('resource-rows').replaceChildren(...rows);
  el('empty-state').hidden = rec_vis.length > 0 || asistencia_vacia;
  document.querySelector('.resource-table').hidden = rec_vis.length === 0 && !asistencia_vacia;
  el('result-count').textContent = `Showing ${rec_vis.length} of ${rec_all.length} resources`;
  const mir_act = el('mirror').value;
  el('origin-note').textContent = `${srv_labels[mir_act]} · complete downloads / Excalibur · PXE & image files`;
  document.querySelectorAll('[data-category]').forEach(btn => {
    const sel = btn.dataset.category === flt_cat;
    btn.classList.toggle('selected',sel);
    btn.setAttribute('aria-pressed',String(sel));
  });
  document.querySelectorAll('[data-tree-node]').forEach(link=>{
    const sel=link.dataset.treeNode===flt_nod;
    link.classList.toggle('selected',sel);
    if(sel) link.setAttribute('aria-current','true');else link.removeAttribute('aria-current');
  });
  if (rec_act && el('resource-dialog').open) act_rec(rec_act);
}

function sel_rama(id) {
  const nodo=nodos_cat.get(id);
  if(!nodo)return;
  flt_nod=id;flt_cat=nodo.category;act_cat();
}

function obt_tam(tam_byt) {
  if (!tam_byt) return 'Recorded after sync';
  const uni = ['B','KiB','MiB','GiB','TiB'];
  const idx = Math.min(4,Math.floor(Math.log(tam_byt)/Math.log(1024)));
  return `${(tam_byt / 1024**idx).toFixed(idx ? 2 : 0)} ${uni[idx]}`;
}

function act_rec(rec) {
  el('resource-title').textContent = rec.name;
  el('resource-description').textContent = rec.description;
  el('resource-meta').replaceChildren();
  const lis_meta = [
    ['Filename',rec.filename],['Category',rec.category === 'assistance' ? 'Remote assistance' : rec.category === 'distribution' ? 'Distros' : 'Tools'],['Media',rec.kind || 'tool'],['Release',rec.release],['Architecture',rec.arch],['Format',rec.format],
    ['Local size',obt_tam(rec.size)],['Local state',rec.status === 'source' ? 'Source URL only' : rec.status],
    ['PXE',rec.pxe_reason || (rec.pxe_ready ? 'Required files found · boot test pending' : 'Generated after sync when supported')],
    ['SHA-256',rec.sha256 || 'Computed after sync; no upstream authentication claim']
  ];
  for (const [nom,val] of lis_meta) {
    const dt = document.createElement('dt');dt.textContent=nom;
    const dd = document.createElement('dd');dd.textContent=val;
    el('resource-meta').append(dt,dd);
  }
  el('resource-servers').replaceChildren(gen_servers(rec));
  el('resource-url').value = obt_url(rec);
  el('resource-download').href = obt_url(rec);
  el('resource-source').href = rec.url;
  el('resource-commands').href = `${url_pxe.replace(/\/$/, '')}/files/${rec.id}.html`;
  const url_tree = obt_contents_url(rec);
  el('resource-contents').hidden = !url_tree;
  if (url_tree) el('resource-contents').href = url_tree;
  else el('resource-contents').removeAttribute('href');
}

function ver_rec(rec) {rec_act=rec;act_rec(rec);el('resource-dialog').showModal();}
function open_details(evt,rec) {
  if(evt.button || evt.ctrlKey || evt.metaKey || evt.shiftKey || evt.altKey || typeof el('resource-dialog').showModal !== 'function') return;
  evt.preventDefault();ver_rec(rec);
}
function ver_toast(txt) {
  clearTimeout(tmr_toast);
  el('toast').textContent = txt;
  el('toast').classList.add('visible');
  tmr_toast = setTimeout(() => el('toast').classList.remove('visible'),2800);
}

async function cop_txt(txt) {
  try {
    await navigator.clipboard.writeText(txt);
    ver_toast('Copied to clipboard');
  } catch {
    // The fallback keeps copy actions useful in HTTP-hosted mirror deployments.
    const tmp = document.createElement('textarea');
    tmp.value = txt;tmp.style.position='fixed';tmp.style.opacity='0';
    (document.querySelector('dialog[open]') || document.body).append(tmp);
    tmp.select();
    const ok = document.execCommand('copy');tmp.remove();
    ver_toast(ok ? 'Copied to clipboard' : 'Copy unavailable. Select the command manually.');
  }
}

function act_mod() {
  const [tit,txt] = mod_desc[mod_act];
  el('mode-title').textContent=tit;el('mode-description').textContent=txt;
  el('deploy-command').textContent = mod_act === 'ftp' ?
    '# Prepared html + cache; inspect with --dry-run first\nsudo bash deploy.sh ftp \\\n  --ftp-host HOST_FTP --ftp-user USUARIO_FTP \\\n  --ftp-root / --verbose' :
    `# Shared paths: fast-boot.json; URLs: ${mod_act === 'ram' ? 'light' : 'heavy'}-url.txt\nsudo bash download.sh --list ${mod_act === 'ram' ? 'light' : 'heavy'} --verbose\nsudo bash deploy.sh ${mod_act} --list ${mod_act === 'ram' ? 'light' : 'heavy'} --verbose\nsudo bash generate.sh --verbose`;
  document.querySelectorAll('[data-mode]').forEach(btn => {
    const sel = btn.dataset.mode === mod_act;btn.classList.toggle('selected',sel);btn.setAttribute('aria-pressed',String(sel));
  });
}

function act_boot() {
  const plat=el('boot-platform').value;
  const met={
    uefi:['Start an x86_64 UEFI iPXE client','Use an iPXE EFI build with the network driver and HTTP support for the target machine. Then enter the following commands at its prompt.'],
    bios:['Start a legacy BIOS iPXE client','Use a BIOS iPXE build from a NIC option ROM, GRUB, or a prepared USB key. The menu checks CPU long-mode support before offering 64-bit kernels.'],
    arm:['Start an ARM64 UEFI iPXE client','Use an ARM64 EFI build for the target board. An x86_64 EFI binary cannot run on ARM hardware; board firmware support is required.']
  }[plat];
  el('boot-method-title').textContent=met[0];el('boot-method-description').textContent=met[1];
  el('boot-command').textContent=cmd_boot;
}

el('search').addEventListener('input',act_cat);
document.querySelectorAll('[data-tree-node]').forEach(link=>link.addEventListener('click',evt=>{
  if(evt.button || evt.ctrlKey || evt.metaKey || evt.shiftKey || evt.altKey)return;
  sel_rama(link.dataset.treeNode);
}));
window.addEventListener('hashchange',()=>{
  const id=window.location.hash.slice(1);
  if(nodos_cat.has(id))sel_rama(id);
  else if(!id || id==='catalog'){flt_nod='';flt_cat='all';act_cat();}
});
for (const nom of ['arch','mirror','sort']) el(nom).addEventListener('change',act_cat);
document.querySelectorAll('[data-category]').forEach(btn => btn.addEventListener('click',()=>{flt_nod='';flt_cat=btn.dataset.category;act_cat();}));
document.querySelectorAll('[data-mode]').forEach(btn => btn.addEventListener('click',()=>{mod_act=btn.dataset.mode;act_mod();}));
document.querySelectorAll('[data-open-boot]').forEach(btn=>btn.addEventListener('click',evt=>{
  if(evt.button || evt.ctrlKey || evt.metaKey || evt.shiftKey || evt.altKey || typeof el('boot-dialog').showModal !== 'function') return;
  evt.preventDefault();el('boot-dialog').showModal();
}));
document.querySelectorAll('[data-copy-boot]').forEach(btn=>btn.addEventListener('click',()=>cop_txt(cmd_boot)));
document.querySelectorAll('[data-close-dialog]').forEach(btn=>btn.addEventListener('click',()=>btn.closest('dialog').close()));
document.querySelectorAll('dialog').forEach(dlg=>dlg.addEventListener('click',evt=>{
  const box=dlg.getBoundingClientRect();
  if(evt.target===dlg && (evt.clientX<box.left||evt.clientX>box.right||evt.clientY<box.top||evt.clientY>box.bottom)) dlg.close();
}));
el('boot-platform').addEventListener('change',act_boot);
el('copy-deploy').addEventListener('click',()=>cop_txt(el('deploy-command').textContent));
el('copy-resource').addEventListener('click',()=>cop_txt(el('resource-url').value));
el('reset-filters').addEventListener('click',()=>{el('search').value='';el('arch').value='all';flt_nod='';flt_cat='all';act_cat();});
document.addEventListener('keydown',evt=>{
  if(evt.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName) && !document.querySelector('dialog[open]')){evt.preventDefault();el('search').focus();}
});
for(const cat of ['all','assistance','distribution','tools']) el(`count-${cat}`).textContent=rec_all.filter(rec=>cat==='all'||rec.category===cat).length;
el('total-count').textContent=rec_all.length;el('side-count').textContent=rec_all.length;
if(dat_cat.state==='synced') {
  el('mirror').value='bastion';
  el('catalog-note').textContent='Local file sizes and SHA-256 hashes are recorded by the generator. PXE file checks do not replace a boot test on target hardware. External mirror availability has not been checked.';
  document.querySelector('.source-label').lastChild.textContent='LOCAL CATALOG';
}
el('mirror').value='bastion';
el('boot-command').textContent=cmd_boot;
document.querySelector('.terminal-url').textContent=`${url_pxe}/menu.ipxe`;
if('IntersectionObserver' in window){
  const nav_obs=new IntersectionObserver(entries=>{
    const vis=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
    if(!vis)return;
    document.querySelectorAll('.side-nav a').forEach(a=>a.classList.toggle('active',a.hash===`#${vis.target.id}`));
  },{rootMargin:'-5% 0px -45% 0px',threshold:[0,.2,.5]});
  for(const nom of ['catalog','network','deployment','project-files']) nav_obs.observe(el(nom));
}
act_cat();act_mod();act_boot();
sel_rama(window.location.hash.slice(1));
// Reveal optional controls only after initialization succeeds. HTML links already work.
document.querySelectorAll('[data-enhance]').forEach(node=>{node.hidden=false;});
