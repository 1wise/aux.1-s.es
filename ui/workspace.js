// Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
// Author & Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  const dat_app=JSON.parse(document.getElementById('workspace-data').textContent);
  const nodo=nom=>document.getElementById(nom);
  const keys=['id','family','release','architecture','kind','download_class','original_url','sha256','size_bytes','name','policy','artifact_type','filename','paths','components','recipe','deploy_method','procedure_url','source_id','source_index','resolved','remote_only','project_url','checksum_source','mirrors','recipe_owner','recipe_notes','architectures','source_artifacts','proposed_boot_method','kernel_params_proposal','worker_queue','ram_min_mb_proposal','notes','provenance'];
  window.AUXCatalog={document:entries=>({schema:'aux-catalog-v8',metadata:{version:dat_app.version},entries:entries.map(e=>Object.fromEntries(keys.filter(k=>e[k]!==undefined).map(k=>[k,e[k]])))})};

  const texto=(tip,txt)=>{const ent=document.createElement(tip);ent.textContent=txt;return ent;};
  function aviso(txt){nodo('app-status').textContent=txt;nodo('app-status').hidden=false;}
  function guarda(nom,txt,tipo='text/plain'){
    const sys_url=URL.createObjectURL(new Blob([txt],{type:tipo}));
    const lnk=document.createElement('a');lnk.href=sys_url;lnk.download=nom;lnk.click();
    setTimeout(()=>URL.revokeObjectURL(sys_url),1000);
  }
  function url_valida(txt){try{const ent=new URL(txt);return ['https:','http:'].includes(ent.protocol)&&!ent.username&&!ent.password?ent.href:null;}catch{return null;}}
  for(const btn of document.querySelectorAll('[data-copy-id]'))btn.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(nodo(btn.dataset.copyId).textContent);aviso('Comando copiado.');}catch{aviso('Seleccionar el texto del comando para copiarlo.');}
  });
  if(document.body.dataset.app==='installer'){
    const roles=nodo('role-options');
    const nat_sel=structuredClone(dat_app.native_defaults);
    for(const [nom,ent] of Object.entries(dat_app.roles)){
      if(nom==='desktop')continue;
      const lab=texto('label','');lab.className='check';const inp=document.createElement('input');
      inp.type='checkbox';inp.name='role';inp.value=nom;inp.checked=true;inp.disabled=nom==='base';
      lab.append(inp,document.createTextNode(ent.label));roles.append(lab);
    }
    function catalogo(){return dat_app.software[nodo('distribution').value];}
    function nativo(){
      const dis=nodo('distribution').value,cat=catalogo(),dat=structuredClone(nat_sel[dis]);
      if(dis==='fedora'){
        const ent=cat.environments.find(ent=>ent.id===dat.environment);
        dat.groups=Array.from(new Set([...(ent?.required||[]),...dat.groups]));
      }else if(dis==='debian'){
        for(const nom of dat.tasks)for(const padre of cat.groups.find(ent=>ent.id===nom).parents)if(!dat.tasks.includes(padre))dat.tasks.push(padre);
      }
      return dat;
    }
    function seleccion(){
      const dis=nodo('distribution').value,nat=nativo();
      const lst=Array.from(document.querySelectorAll('input[name=role]:checked')).map(ent=>ent.value);
      const ids=dis==='debian'?nat.tasks:nat.groups;
      const nat_paq=dis==='fedora'?ids.map(nom=>'@'+nom):ids.flatMap(nom=>catalogo().groups.find(ent=>ent.id===nom).packages);
      const paq=Array.from(new Set([...nat_paq,...lst.flatMap(nom=>dat_app.roles[nom][dis].split(/\s+/))]));
      const modo=nodo('install-mode').value;
      const dat={schema:'aux-install-v1',distribution:dis,roles:lst,native:nat,mode:modo,root:modo==='root'?nodo('root-path').value.trim():'/'};
      if(nodo('identity-apply').checked){dat.identity={};for(const k of ['hostname','locale','timezone','user']){const v=nodo('identity-'+k).value.trim();if(v)dat.identity[k]=k==='hostname'?v.toLowerCase():v;}}
      if(dat.identity){const i=dat.identity;const extra=[];if(i.timezone)extra.push('tzdata');if(i.locale){if(dis==='debian')extra.push('locales');else if(dis==='alpine')extra.push('musl-locales','musl-locales-lang');else if(!['C','C.UTF-8','POSIX'].includes(i.locale))extra.push('glibc-langpack-'+i.locale.split('_')[0]);}for(const p of extra)if(!paq.includes(p))paq.push(p);}
      if(modo==='iso')Object.assign(dat,{iso:nodo('iso-path').value.trim(),iso_sha256:nodo('iso-sha').value.trim(),output:nodo('iso-output').value.trim()});
      return {dat,paq,ids};
    }
    function muestra_grupos(){
      const dis=nodo('distribution').value,cat=catalogo(),nat=nativo(),bus=nodo('software-search').value.toLowerCase();
      const ids=dis==='debian'?nat.tasks:nat.groups;
      const ent=cat.environments.find(ent=>ent.id===nat.environment),req=ent?.required||[];
      let visibles=0;
      for(const lab of nodo('native-options').querySelectorAll('label')){
        const inp=lab.querySelector('input'),ent=cat.groups.find(ent=>ent.id===inp.value);
        inp.checked=ids.includes(ent.id);inp.disabled=req.includes(ent.id);
        const avanzado=dis==='debian'?ent.section==='l10n':!ent.visible;
        lab.hidden=bus?![ent.id,ent.label,ent.description].join(' ').toLowerCase().includes(bus):avanzado&&!nodo('software-advanced').checked&&!inp.checked;
        if(!lab.hidden)visibles++;
        lab.classList.toggle('required',inp.disabled);
      }
      nodo('software-count').textContent=visibles+' visibles de '+cat.groups.length+' '+(dis==='debian'?'tareas':'grupos')+' · '+ids.length+' elegidos';
    }
    function pinta_nativo(){
      const dis=nodo('distribution').value,cat=catalogo(),fed=dis==='fedora';
      nodo('software-source').textContent=(fed?'Fedora '+cat.release+' · '+cat.environments.length+' entornos y '+cat.groups.length+' grupos':dis==='alpine'?'Alpine '+cat.release+' · '+cat.groups.length+' colecciones AUX / apk':'Debian Testing · tasksel '+cat.tasksel_version+' · '+cat.groups.length+' tareas')+' · catálogo del '+cat.retrieved_at;
      nodo('environment-field').hidden=!fed;nodo('environment-description').hidden=!fed;
      nodo('advanced-label').textContent=fed?'Mostrar grupos internos':'Mostrar tareas de idiomas';
      nodo('advanced-label').parentElement.hidden=dis==='alpine';
      const sel=nodo('native-environment');sel.replaceChildren(new Option('Solo grupos / sin entorno',''));
      for(const ent of cat.environments)sel.add(new Option(ent.label,ent.id));
      if(fed)sel.value=nat_sel.fedora.environment;
      nodo('environment-description').textContent=cat.environments.find(ent=>ent.id===sel.value)?.description||'';
      const caja=nodo('native-options');caja.replaceChildren(texto('legend',fed?'Grupos requeridos y complementos':dis==='alpine'?'Colecciones AUX de paquetes apk':'Tareas nativas de Debian'));
      for(const ent of cat.groups){
        const lab=texto('label','');lab.className='software-choice';const inp=document.createElement('input');
        inp.type='checkbox';inp.name='native';inp.value=ent.id;inp.setAttribute('aria-label',ent.label+' ('+ent.id+')');
        const det=texto('span','');det.append(texto('strong',ent.label),texto('small',ent.id));
        if(ent.description!==ent.label)det.append(texto('small',ent.description.split('\n')[0]));
        lab.append(inp,det);caja.append(lab);
        inp.addEventListener('change',()=>{
          const nat=nat_sel[dis],campo=dis==='debian'?'tasks':'groups',act=new Set(nat[campo]);
          if(inp.checked)act.add(ent.id);else{
            act.delete(ent.id);
            if(dis==='debian')for(const hijo of cat.groups)if(hijo.parents.includes(ent.id))act.delete(hijo.id);
          }
          nat[campo]=Array.from(act);actualiza();
        });
      }
      actualiza();
    }
    function actualiza(){
      const {dat,paq,ids}=seleccion();
      nodo('root-field').hidden=dat.mode!=='root';nodo('iso-fields').hidden=dat.mode!=='iso';
      const actual=dat.mode==='existing';
      nodo('target-description').textContent=actual?
        'DESTINO: SISTEMA ACTUAL. Instala paquetes y aplicaciones sobre el equipo donde se ejecute aux-setup y puede modificar sus servicios y configuración.':
        dat.mode==='iso'&&dat.distribution==='alpine'?'Conservar setup-alpine y añadir un perfil explícito para aplicar después de instalar Alpine.':
        dat.mode==='root'?'Preparar una base en un directorio vacío. El disco arrancable requiere completar particiones, cuenta y cargador.':
        'Preparar una ISO oficial personalizada para instalar en el equipo de destino.';
      nodo('target-description').classList.toggle('host-target',actual);
      nodo('apply-heading').textContent=actual?'Aplicar SOBRE EL SISTEMA ACTUAL':'Aplicar la selección revisada';
      nodo('selection-summary').textContent=ids.length+' '+(dat.distribution==='debian'?'tareas nativas':'grupos nativos')+' · '+dat.roles.length+' complementos AUX · '+paq.length+' solicitudes de paquetes/grupos';
      nodo('selected-packages').textContent=paq.join('\n');
      nodo('setup-plan').textContent='python3 aux-setup --selection aux-selection.json';
      nodo('setup-apply').textContent='sudo python3 aux-setup --selection aux-selection.json --apply'+(dat.mode==='iso'?' --check-packages':'');
      nodo('setup-error').hidden=true;muestra_grupos();
    }
    function valido(dat){
      const i=dat.identity||{};
      if(i.hostname&&(i.hostname.length>253||!i.hostname.split('.').every(v=>/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(v))))throw Error('Revisar el hostname del equipo.');
      if(i.locale&&!/^(?:C|POSIX|[a-z]{2,3}(?:_[A-Z]{2})?)(?:\.(?:UTF-8|utf8))?$/.test(i.locale))throw Error('Revisar el locale.');
      if(i.timezone){try{new Intl.DateTimeFormat('en',{timeZone:i.timezone});}catch{throw Error('Revisar la zona IANA.');}}
      if(i.user&&(!/^[a-z_][a-z0-9_-]{0,31}$/.test(i.user)||['root','bin','daemon','sys','sync','nobody','osquery','aux-ai','aux-catalog'].includes(i.user)))throw Error('Revisar el usuario personal.');

      if(dat.mode==='root'&&(!dat.root.startsWith('/')||dat.root==='/'))throw new Error('Indicar una raíz nueva absoluta distinta de /.');
      if(dat.mode==='iso'&&(!dat.iso||!dat.output||!/^[a-fA-F0-9]{64}$/.test(dat.iso_sha256)))throw new Error('Completar las rutas ISO y el SHA-256 del medio comprobado.');
    }
    nodo('distribution').addEventListener('change',()=>{nodo('software-search').value='';nodo('software-advanced').checked=false;pinta_nativo();});
    nodo('native-environment').addEventListener('change',()=>{
      const nom=nodo('native-environment').value,ent=catalogo().environments.find(ent=>ent.id===nom);
      nat_sel.fedora.environment=nom;nat_sel.fedora.groups=ent?.default.slice()||[];
      nodo('environment-description').textContent=ent?.description||'';actualiza();
    });
    nodo('setup-form').addEventListener('change',actualiza);
    // Choice controls commit in change handlers before the summary redraws them.
    nodo('setup-form').addEventListener('input',evt=>{if(evt.target.matches('input:not([type=checkbox])'))actualiza();});
    nodo('setup-form').addEventListener('submit',evt=>evt.preventDefault());
    nodo('download-selection').addEventListener('click',()=>{try{const {dat}=seleccion();valido(dat);guarda('aux-selection.json',JSON.stringify(dat,null,2)+'\n','application/json');}catch(exc){nodo('setup-error').textContent=exc.message;nodo('setup-error').hidden=false;}});
    nodo('download-profile').addEventListener('click',()=>{
      const {dat,paq}=seleccion();try{valido(dat);}catch(e){aviso(e.message);return;}let perfil=dat_app.templates[dat.distribution];
      if(dat.distribution==='fedora'){
        perfil=perfil.replace(/%packages\n[\s\S]*?%end/,'%packages\n@core\n'+paq.join('\n')+'\n%end');
        if(!paq.some(nom=>nom.includes('desktop')||nom==='@base-x'))perfil=perfil.replace('xconfig --startxonboot\n','');
      }
      else if(dat.distribution==='alpine')perfil=perfil.replace('__AUX_PACKAGES__',paq.join(' '));
      else perfil=perfil.replace(/^d-i pkgsel\/include string .*$/m,'d-i pkgsel/include string '+paq.join(' ')).replace(/^tasksel tasksel\/first multiselect .*$/m,'tasksel tasksel/first multiselect '+dat.native.tasks.join(', '));
      const i=dat.identity||{};
      if(dat.distribution==='fedora'){
        if(i.locale)perfil=perfil.replace(/^lang .*$/m,'lang '+i.locale);
        if(i.timezone)perfil=perfil.replace(/^timezone .*$/m,'timezone '+i.timezone+' --utc');
        if(i.hostname)perfil=perfil.replace(/^(network .*)$/m,'$1 --hostname='+i.hostname);
        if(i.user)perfil+='\n# Set the personal password in the installer or with passwd before use.\nuser --name='+i.user+' --lock\nfirstboot --enable\n';
      }else if(dat.distribution==='debian'){
        if(i.locale)perfil=perfil.replace(/^d-i debian-installer\/locale string .*$/m,'d-i debian-installer/locale string '+i.locale);
        if(i.timezone)perfil=perfil.replace(/^d-i time\/zone string .*$/m,'d-i time/zone string '+i.timezone);
        if(i.hostname)perfil+='\nd-i netcfg/get_hostname string '+i.hostname+'\nd-i netcfg/hostname string '+i.hostname+'\n';
        if(i.user)perfil+='\nd-i passwd/user-fullname string '+i.user+'\nd-i passwd/username string '+i.user+'\n# The installer still requests the password interactively.\n';
      }else if(Object.keys(i).length){
        perfil+='\n# Explicit target identity; passwords are configured locally.\n';
        if(i.hostname)perfil+="printf '%s\\n' "+i.hostname+' > /etc/hostname\n';
        if(i.locale)perfil+="printf '%s\\n' 'export LANG="+i.locale+"' > /etc/profile.d/aux-locale.sh\n";
        if(i.timezone)perfil+='ln -snf /usr/share/zoneinfo/'+i.timezone+' /etc/localtime\n';
        if(i.user)perfil+='id -u '+i.user+' >/dev/null 2>&1 || adduser -D -s /bin/ash '+i.user+'\n';
      }
      guarda(dat.distribution==='fedora'?'installed.ks':dat.distribution==='alpine'?'apply-alpine.sh':'preseed.cfg',perfil);
    });
    pinta_nativo();
  }
  if(document.body.dataset.app==='catalogue'){
    let ents=dat_app.entries;const elegidos=new Map(),manual=new Set(),automaticos=new Set();
    const valid=ent=>ent&&typeof ent.id==='string'&&url_valida(ent.original_url)&&/^[0-9A-F]{3}$/i.test(ent.policy||'');
    function filtros(){for(const [nom,campo] of [['catalog-family','family'],['catalog-arch','architecture'],['catalog-format','kind']]){
      const sel=nodo(nom),ant=sel.value;sel.replaceChildren(new Option('Todos','all'));
      for(const val of [...new Set(ents.map(ent=>ent[campo]))].sort())sel.add(new Option(val,val));
      sel.value=Array.from(sel.options).some(ent=>ent.value===ant)?ant:'all';
    }}
    function visibles(){const bus=nodo('catalog-search').value.toLowerCase();return ents.filter(ent=>
      (!bus||[ent.name,ent.family,ent.release,ent.architecture,ent.kind].join(' ').toLowerCase().includes(bus))&&
      [['catalog-family','family'],['catalog-arch','architecture'],['catalog-format','kind']].every(([nom,campo])=>nodo(nom).value==='all'||nodo(nom).value===ent[campo]));}
    function cuenta(){nodo('catalog-count').textContent=visibles().length+' resultados · '+elegidos.size+' elegidos';nodo('export-catalog').disabled=!elegidos.size;}
    function cambia(ent,pol){ent.policy=pol.toString(16).toUpperCase().padStart(3,'0');manual.add(ent.id);elegidos.set(ent.id,{...ent});}
    function pinta(){const rows=nodo('catalog-rows');rows.replaceChildren();const lista=visibles();
      for(const original of lista){
        const ent=elegidos.get(original.id)||original;
        ent.policy=(ent.policy||'004').toUpperCase();const fil=document.createElement('tr'),cel=document.createElement('td'),inp=document.createElement('input');
        inp.type='checkbox';inp.checked=elegidos.has(ent.id);inp.setAttribute('aria-label','Elegir '+ent.name);inp.dataset.entryId=ent.id;
        inp.addEventListener('change',()=>{manual.add(ent.id);if(inp.checked)elegidos.set(ent.id,{...ent});else elegidos.delete(ent.id);cuenta();});cel.append(inp);fil.append(cel);
        const nom=document.createElement('td');nom.append(texto('strong',ent.name||ent.family),texto('small',ent.release));
        const det=document.createElement('details');det.append(texto('summary','Fuente, integridad y prueba'));
        det.append(texto('pre','SHA-256 oficial: '+(ent.sha256||'sin resolver')+'\nEstado RASCDE: '+(ent.word24||'sin checkstatus')+'\nComprobada exige arranque hasta login.'));
        if(ent.procedure_url){const l=texto('a','Procedimiento de origen');l.href=url_valida(ent.procedure_url);det.append(l);}nom.append(det);fil.append(nom);
        for(const campo of ['architecture','kind'])fil.append(texto('td',ent[campo]));
        const pol=document.createElement('td'),val=document.createElement('input');val.value=ent.policy;val.maxLength=3;val.size=4;val.setAttribute('aria-label','Política CDE de '+ent.id);
        val.addEventListener('input',()=>{const txt=val.value.toUpperCase();const ok=/^[0-9A-F]{3}$/.test(txt)&&(!ent.remote_only||!(parseInt(txt,16)&11));
          val.setCustomValidity(ok?'':'Usar tres hexadecimales; un menú remoto permite solo origen.');
          if(ok){cambia(ent,parseInt(txt,16));cuenta();}});pol.append(val);
        for(const [rot,bit] of [['RAM',1],['SSD',2],['Origen',4],['Bastion',8],['Descargar',16]]){
          const lab=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.checked=!!(parseInt(ent.policy,16)&bit);
          box.disabled=!!ent.remote_only&&bit!==4;box.setAttribute('aria-label',ent.id+' · '+rot);
          box.addEventListener('change',()=>{const n=parseInt(ent.policy,16);cambia(ent,box.checked?n|bit:n&~bit);pinta();});lab.append(box,document.createTextNode(rot));pol.append(lab);
        }fil.append(pol);
        const links=document.createElement('td');
        for(const [rot,url] of [['Origen exacto',ent.original_url],['Índice oficial',ent.source_index],...Object.entries(ent.download_urls||{})]){
          const dest=url_valida(url);if(dest){const l=texto('a',rot);l.href=dest;l.rel='noopener noreferrer';links.append(l);}}
        fil.append(links);rows.append(fil);
      }
      nodo('select-visible').checked=lista.length>0&&lista.every(ent=>elegidos.has(ent.id));cuenta();
    }
    for(const nom of ['catalog-search','catalog-family','catalog-arch','catalog-format'])nodo(nom).addEventListener(nom==='catalog-search'?'input':'change',pinta);
    nodo('select-visible').addEventListener('change',()=>{for(const ent of visibles()){manual.add(ent.id);if(nodo('select-visible').checked)elegidos.set(ent.id,{...ent});else elegidos.delete(ent.id);}pinta();});
    const cajas=Array.from(document.querySelectorAll('#catalog-presets input'));
    for(const box of cajas)box.addEventListener('change',()=>{
      if(box.value==='todos'){for(const x of cajas)if(x.value!=='todos')x.checked=box.checked;}
      else {const todo=cajas.find(x=>x.value==='todos');todo.checked=cajas.filter(x=>x.value!=='todos').every(x=>x.checked);}
      const familias=new Set(cajas.filter(x=>x.checked&&x.value!=='todos').map(x=>x.value));
      for(const id of automaticos)if(!manual.has(id))elegidos.delete(id);automaticos.clear();
      for(const ent of ents){const comun=ent.deploy_method==='chroot'&&ent.procedure_url;
        const afinidad=ent.presets||[ent.family];if(!comun&&!afinidad.some(x=>familias.has(x)))continue;
        if(comun&&!familias.size||manual.has(ent.id))continue;
        const key=ent.remote_only?'origin_policy_bits':ent.download_class==='heavy'||comun?'heavy_policy_bits':'light_policy_bits';
        const mascara=parseInt((dat_app.catalog_presets||{})[key]||({origin_policy_bits:'004',heavy_policy_bits:'016',light_policy_bits:'015'})[key],16);
        const copia={...ent,policy:(parseInt(ent.policy,16)|mascara).toString(16).toUpperCase().padStart(3,'0')};
        elegidos.set(ent.id,copia);automaticos.add(ent.id);
      }pinta();
    });
    nodo('export-catalog').addEventListener('click',()=>{
      const lista=Array.from(elegidos.values());if(lista.some(ent=>!valid(ent))){aviso('Corregir las políticas antes de exportar.');return;}
      guarda('catalog.json',JSON.stringify(window.AUXCatalog.document(lista),null,2)+'\n','application/json');
    });
    nodo('load-live').addEventListener('click',async()=>{try{
      const url=url_valida(nodo('catalog-live-url').value);if(!url)throw new Error('Indicar una URL HTTP/HTTPS válida.');
      const rsp=await fetch(url,{cache:'no-store',credentials:'omit'});if(!rsp.ok)throw new Error('Catálogo no disponible ('+rsp.status+').');
      const dat=await rsp.json();if(dat.schema!=='aux-catalog-v8'||!Array.isArray(dat.entries)||dat.entries.length>10000||dat.entries.some(ent=>!valid(ent)))throw new Error('Se requiere un catálogo AUX 8 válido.');
      const mapa=new Map(ents.map(ent=>[ent.id,ent]));for(const ent of dat.entries)if(!manual.has(ent.id))mapa.set(ent.id,{...ent,name:ent.name||ent.id});
      ents=Array.from(mapa.values());filtros();pinta();nodo('catalog-live-status').textContent='Catálogo leído; se conservan las decisiones manuales.';
    }catch(exc){nodo('catalog-live-status').textContent=exc.message+' La selección anterior se conserva.';}});
    nodo('catalog-search').value=new URLSearchParams(location.search).get('q')||'';filtros();pinta();
  }
  if(document.body.dataset.app==='adapt')nodo('evolve-export').addEventListener('click',()=>{
    const goal=nodo('evolve-goal').value.trim(),max=Number(nodo('evolve-tokens').value);if(!goal||!Number.isInteger(max)||max<512||max>16384){aviso('Describir el objetivo y revisar Max tokens.');return;}
    guarda('aux-adaptation-request.json',JSON.stringify({schema:'aux-adaptation-brief-v1',version:dat_app.version,goal,provider:nodo('evolve-provider').value,model:nodo('evolve-model').value.trim(),max_tokens:max,products:{recipes:dat_app.products.recipes.map(e=>e.id),policy:'CDE',status:'RASCDE; 20 visible bits; A/S observed'},next_step:'./aux self-assamble --request aux-adaptation-request.json --interactive'},null,2)+'\n','application/json');
  });
  if(document.body.dataset.app==='systems')nodo('open-cockpit').addEventListener('click',()=>{
    const url=url_valida(nodo('cockpit-url').value);if(!url||!url.startsWith('https://')){nodo('cockpit-status').textContent='Indicar la dirección HTTPS del equipo de destino.';return;}
    window.open(url,'_blank','noopener,noreferrer');
  });
})();
