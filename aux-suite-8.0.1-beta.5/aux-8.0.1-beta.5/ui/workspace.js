// Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
// Author & Credits: https://www.alawise.es/1-s
'use strict';
(() => {
  window.AUXCapacity=(entries,opt,selected=[])=>{
    const gib=1024**3,dests=['ram','ssd','bastion'],sel=new Set(selected),zero=()=>Object.fromEntries(dests.map(k=>[k,0]));
    const physical={ram:Math.floor(opt.ram_budget_gib*gib*(1-opt.ram_reserve_percent/100)),ssd:Math.floor(opt.ssd_budget_gib*gib),bastion:Math.floor(opt.ssd_budget_gib*gib)};
    const limits=Object.fromEntries(dests.map(k=>[k,Math.min(physical[k],sel.size?sel.size*(k==='ram'?opt.preset_ram_gib:opt.preset_ssd_gib)*gib:physical[k])]));
    const images=zero(),deploys=zero(),cache=zero(),shared=zero(),unknown=[],estimated=[],seen=new Set();
    for(const ent of entries){
      if(seen.has(ent.id)||ent.remote_only)continue;seen.add(ent.id);
      const bits=parseInt(ent.policy,16),loc=dests.filter((k,i)=>bits&({ram:1,ssd:2,bastion:8})[k]);
      if(!loc.length&&!(bits&48))continue;
      const size=ent.size_bytes;if(!size){unknown.push(ent.id);continue;}const cost=zero();
      images.ssd+=size;cache.ssd+=size;cost.ssd+=size;
      for(const dest of loc){
        const iso=ent.artifact_type==='iso',mounted=iso&&dest==='ssd'&&opt.ssd_mode==='mount';
        if(!mounted){images[dest]+=size;cost[dest]+=size;}
        if(iso&&dest==='ssd'&&!mounted){const extra=ent.deployment_size_bytes??size;deploys[dest]+=extra;cost[dest]+=extra;if(ent.deployment_size_bytes===undefined)estimated.push(ent.id);}
      }
      const affinity=ent.deploy_method==='chroot'&&ent.procedure_url?['alpine','fedora','debian']:(ent.presets||[ent.family]);
      const repeats=Math.max(0,affinity.filter(k=>sel.has(k)).length-1);for(const k of dests)shared[k]+=cost[k]*repeats;
    }
    const total=Object.fromEntries(dests.map(k=>[k,images[k]+deploys[k]]));
    return {images_bytes:images,deploy_bytes:deploys,cache_bytes:cache,selected_bytes:total,budget_bytes:limits,shared_savings_bytes:shared,
      remaining_bytes:Object.fromEntries(dests.map(k=>[k,limits[k]-total[k]])),unknown_sizes:unknown,estimated_deployments:estimated,over_budget:dests.filter(k=>total[k]>limits[k])};
  };

  const dat_app=JSON.parse(document.getElementById('workspace-data').textContent);
  const nodo=nom=>document.getElementById(nom);
  const keys=['id','family','release','architecture','kind','download_class','original_url','sha256','size_bytes','name','priority','priority_sectors','policy','artifact_type','filename','paths','components','recipe','deploy_method','procedure_url','source_id','source_index','resolved','remote_only','project_url','checksum_source','mirrors','recipe_owner','recipe_notes','architectures','source_artifacts','proposed_boot_method','kernel_params_proposal','worker_queue','ram_min_mb_proposal','notes','provenance','signature_source','signature_verification','hash_origin','deployment_size_bytes'];
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
      inp.type='checkbox';inp.name='role';inp.value=nom;inp.checked=!['kernel-modeler','aux-assist','admin'].includes(nom);inp.disabled=nom==='base';
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
      const dis=nodo('distribution').value,nat=nativo(),workbench=nodo('install-mode').value==='kernel-modeler';
      const modeler=document.querySelector('input[name=role][value=kernel-modeler]');modeler.disabled=workbench;if(workbench)modeler.checked=true;
      const lst=Array.from(document.querySelectorAll('input[name=role]:checked')).map(ent=>ent.value);
      const ids=dis==='debian'?nat.tasks:nat.groups;
      const nat_paq=dis==='fedora'?ids.map(nom=>'@'+nom):ids.flatMap(nom=>catalogo().groups.find(ent=>ent.id===nom).packages);
      const paq=Array.from(new Set([...nat_paq,...lst.flatMap(nom=>dat_app.roles[nom][dis].split(/\s+/))]));
      const modo=workbench?nodo('kernel-target-mode').value:nodo('install-mode').value;
      const dat={schema:'aux-install-v1',distribution:dis,roles:lst,native:nat,mode:modo,root:modo==='root'?nodo('root-path').value.trim():'/'};
      if(workbench){dat.mode='kernel-modeler';dat.target_mode=modo;if(!dat.roles.includes('kernel-modeler'))dat.roles.push('kernel-modeler');}
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
      const destination=dat.target_mode||dat.mode;
      nodo('kernel-modeler-fields').hidden=dat.mode!=='kernel-modeler';
      nodo('root-field').hidden=destination!=='root';nodo('iso-fields').hidden=destination!=='iso';
      const actual=destination==='existing';
      nodo('target-description').textContent=actual?
        'DESTINO: SISTEMA ACTUAL. Instala paquetes y aplicaciones sobre el equipo donde se ejecute aux-setup y puede modificar sus servicios y configuración.':
        destination==='iso'&&dat.distribution==='alpine'?'Conservar setup-alpine y añadir un perfil explícito para aplicar después de instalar Alpine.':
        destination==='root'?'Preparar una base en un directorio vacío. El disco arrancable requiere completar particiones, cuenta y cargador.':
        'Preparar una ISO oficial personalizada para instalar en el equipo de destino.';
      nodo('target-description').classList.toggle('host-target',actual);
      nodo('apply-heading').textContent=actual?'Aplicar SOBRE EL SISTEMA ACTUAL':'Aplicar la selección revisada';
      nodo('selection-summary').textContent=ids.length+' '+(dat.distribution==='debian'?'tareas nativas':'grupos nativos')+' · '+dat.roles.length+' complementos AUX · '+paq.length+' solicitudes de paquetes/grupos';
      nodo('selected-packages').textContent=paq.join('\n');
      nodo('setup-plan').textContent='python3 aux-setup --selection aux-selection.json';
      nodo('setup-apply').textContent='sudo python3 aux-setup --selection aux-selection.json --apply'+(destination==='iso'?' --check-packages':'');
      nodo('setup-error').hidden=true;muestra_grupos();
    }
    function valido(dat){
      const i=dat.identity||{};
      if(i.hostname&&(i.hostname.length>253||!i.hostname.split('.').every(v=>/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(v))))throw Error('Revisar el hostname del equipo.');
      if(i.locale&&!/^(?:C|POSIX|[a-z]{2,3}(?:_[A-Z]{2})?)(?:\.(?:UTF-8|utf8))?$/.test(i.locale))throw Error('Revisar el locale.');
      if(i.timezone){try{new Intl.DateTimeFormat('en',{timeZone:i.timezone});}catch{throw Error('Revisar la zona IANA.');}}
      if(i.user&&(!/^[a-z_][a-z0-9_-]{0,31}$/.test(i.user)||['root','bin','daemon','sys','sync','nobody','osquery','aux-ai','aux-catalog'].includes(i.user)))throw Error('Revisar el usuario personal.');

      const destination=dat.target_mode||dat.mode;
      if(destination==='root'&&(!dat.root.startsWith('/')||dat.root==='/'))throw new Error('Indicar una raíz nueva absoluta distinta de /.');
      if(destination==='iso'&&(!dat.iso||!dat.output||!/^[a-fA-F0-9]{64}$/.test(dat.iso_sha256)))throw new Error('Completar las rutas ISO y el SHA-256 del medio comprobado.');
    }
    function kernelDefaults(){
      const dis=nodo('distribution').value;nat_sel[dis]=structuredClone(dat_app.kernel_native_defaults[dis]);
      for(const inp of document.querySelectorAll('input[name=role]'))inp.checked=['base','kernel-modeler'].includes(inp.value);
    }
    nodo('install-mode').addEventListener('change',()=>{if(nodo('install-mode').value==='kernel-modeler'){kernelDefaults();pinta_nativo();}else actualiza();});
    nodo('distribution').addEventListener('change',()=>{if(nodo('install-mode').value==='kernel-modeler')kernelDefaults();nodo('software-search').value='';nodo('software-advanced').checked=false;pinta_nativo();});
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
  if(['catalogue','status'].includes(document.body.dataset.app)){
    let ents=dat_app.entries;const elegidos=new Map(),manual=new Set(),automaticos=new Set();
    let restoring=true;const storageKey='aux-board:'+dat_app.version+':'+dat_app.entries.map(e=>e.identity||e.id).join('|');
    function persist(){if(restoring)return;try{sessionStorage.setItem(storageKey,JSON.stringify({entries:ents.map(e=>({id:e.id,identity:e.identity,policy:e.policy,priority:e.priority||'0'})),selected:Array.from(elegidos.keys()),manual:Array.from(manual),automatic:Array.from(automaticos),presets:selectedPresets(),limits:limits()}));}catch{}}
    const valid=ent=>ent&&typeof ent.id==='string'&&url_valida(ent.original_url)&&/^[0-9A-F]{3}$/i.test(ent.policy||'')&&/^[0-9A-F]$/i.test(ent.priority||'0');
    function filtros(){for(const [nom,campo] of [['catalog-family','family'],['catalog-arch','architecture'],['catalog-format','kind']]){
      const sel=nodo(nom),ant=sel.value;sel.replaceChildren(new Option('Todos','all'));
      for(const val of [...new Set(ents.map(ent=>ent[campo]))].sort())sel.add(new Option(val,val));
      sel.value=Array.from(sel.options).some(ent=>ent.value===ant)?ant:'all';
    }}
    function visibles(){const bus=nodo('catalog-search').value.toLowerCase();return ents.filter(ent=>
      (!bus||[ent.id,ent.name,ent.family,ent.release,ent.architecture,ent.kind,ent.original_url].join(' ').toLowerCase().includes(bus))&&
      [['catalog-family','family'],['catalog-arch','architecture'],['catalog-format','kind']].every(([nom,campo])=>nodo(nom).value==='all'||nodo(nom).value===ent[campo]));}
    function selectedPresets(){return Array.from(document.querySelectorAll('#catalog-presets input:checked')).map(x=>x.value).filter(x=>x!=='todos');}
    function limits(){const opt={...dat_app.capacity_defaults};for(const key of ['ram_budget_gib','ssd_budget_gib','preset_ram_gib','preset_ssd_gib'])opt[key]=Number(nodo('capacity-'+key).value);opt.ssd_mode=nodo('capacity-ssd_mode').value;return opt;}
    function capacity(){
      const opt=limits(),valid=Object.entries(opt).filter(([k])=>k!=='ssd_mode').every(([,v])=>Number.isFinite(v)&&v>=0);
      if(!valid){nodo('capacity-notes').textContent='Revisar los presupuestos.';return;}
      const dat=window.AUXCapacity(Array.from(elegidos.values()),opt,selectedPresets()),rows=nodo('capacity-rows');rows.replaceChildren();
      for(const key of ['ram','ssd','bastion']){const row=document.createElement('tr');for(const value of [key.toUpperCase(),...['images_bytes','deploy_bytes','selected_bytes','budget_bytes','remaining_bytes'].map(field=>(dat[field][key]/1024**3).toFixed(2))])row.append(texto('td',value));row.classList.toggle('capacity-over',dat.over_budget.includes(key));rows.append(row);}
      nodo('capacity-notes').textContent='Pendientes de tamaño: '+dat.unknown_sizes.length+' · Deploys estimados: '+dat.estimated_deployments.length+' · Ahorro por recursos compartidos: '+Object.entries(dat.shared_savings_bytes).map(([k,v])=>k.toUpperCase()+' '+(v/1024**3).toFixed(2)+' GiB').join(', ')+(dat.over_budget.length?' · EXCEDIDO: '+dat.over_budget.join(', '):' · El margen permite añadir recursos manualmente.');
      nodo('capacity-cache').textContent='Caché SSD incluida en imágenes: '+(dat.cache_bytes.ssd/1024**3).toFixed(2)+' GiB. Un tamaño pendiente impide acreditar que el conjunto cabe.';
    }
    function cuenta(){nodo('catalog-count').textContent=visibles().length+' resultados · '+elegidos.size+' elegidos';nodo('workflow-summary').textContent=elegidos.size+' recursos · Download '+Array.from(elegidos.values()).filter(e=>parseInt(e.policy,16)&48).length+' · Deploy '+Array.from(elegidos.values()).filter(e=>parseInt(e.policy,16)&11).length;persist();nodo('export-catalog').disabled=!elegidos.size;capacity();}
    function cambia(ent,pol){ent.policy=pol.toString(16).toUpperCase().padStart(3,'0');manual.add(ent.id);elegidos.set(ent.id,{...ent});}
    function pinta(){const rows=nodo('catalog-rows');rows.replaceChildren();const lista=visibles();
      for(const original of lista){
        const ent=elegidos.get(original.id)||original,obs=dat_app.status.entries[ent.id]||{};
        rows.append(...window.AUXBoard.row(ent,obs,dat_app.status,elegidos.has(ent.id),checked=>{manual.add(ent.id);if(checked)elegidos.set(ent.id,{...ent});else elegidos.delete(ent.id);cuenta();},edited=>{Object.assign(original,{policy:edited.policy,priority:edited.priority});cambia(edited,parseInt(edited.policy,16));cuenta();}));
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
      const result=Array.from(elegidos.values());let deferred=0;
      const priority=e=>{const p=parseInt(e.priority||'0',16),scope=e.priority_sectors?.length?e.priority_sectors:(e.presets||[e.family]),sector=scope.some(x=>familias.has(x));return [p&4?0:1,p&1?0:1,p&2&&sector?0:1,p&8&&sector?0:1,e.deploy_method==='chroot'?0:e.recipe?.approved?1:e.download_class!=='heavy'?2:3,['x86_64','amd64'].includes(e.architecture)?0:1,e.size_bytes||0,e.id];};
      const candidates=ents.filter(ent=>{const common=ent.deploy_method==='chroot'&&ent.procedure_url;return common?familias.size:(ent.presets||[ent.family]).some(x=>familias.has(x));}).sort((a,b)=>{const x=priority(a),y=priority(b);for(let i=0;i<x.length;i++)if(x[i]!==y[i])return x[i]<y[i]?-1:1;return 0;});
      for(const ent of candidates){
        if(manual.has(ent.id))continue;
        const common=ent.deploy_method==='chroot'&&ent.procedure_url,key=ent.remote_only?'origin_policy_bits':ent.download_class==='heavy'||common?'heavy_policy_bits':'light_policy_bits';
        const mask=parseInt((dat_app.catalog_presets||{})[key]||({origin_policy_bits:'004',heavy_policy_bits:'016',light_policy_bits:'015'})[key],16);
        const copy={...ent,policy:(parseInt(ent.policy,16)|mask).toString(16).toUpperCase().padStart(3,'0')};
        if(window.AUXCapacity([...result,copy],limits(),Array.from(familias)).over_budget.length&&!ent.remote_only&&!(parseInt(ent.priority||'0',16)&4)){copy.policy=((parseInt(ent.policy,16)&~0x3b)|4).toString(16).toUpperCase().padStart(3,'0');deferred++;}
        result.push(copy);elegidos.set(ent.id,copy);automaticos.add(ent.id);
      }
      nodo('capacity-deferred').textContent=deferred+' recursos conservados en origen por presupuesto. Cambiar su política permite ampliar manualmente.';
      pinta();
    });
    nodo('export-catalog').addEventListener('click',()=>{
      const lista=Array.from(elegidos.values());if(lista.some(ent=>!valid(ent))){aviso('Corregir las políticas antes de exportar.');return;}
      const dat=window.AUXCatalog.document(lista);dat.planning={presets:selectedPresets(),...limits()};
      guarda('catalog.json',JSON.stringify(dat,null,2)+'\n','application/json');
    });
    nodo('load-live').addEventListener('click',async()=>{try{
      const url=url_valida(nodo('catalog-live-url').value);if(!url)throw new Error('Indicar una URL HTTP/HTTPS válida.');
      const rsp=await fetch(url,{cache:'no-store',credentials:'omit'});if(!rsp.ok)throw new Error('Catálogo no disponible ('+rsp.status+').');
      const dat=await rsp.json();if(dat.schema!=='aux-catalog-v8'||!Array.isArray(dat.entries)||dat.entries.length>10000||dat.entries.some(ent=>!valid(ent)))throw new Error('Se requiere un catálogo AUX 8 válido.');
      const mapa=new Map(ents.map(ent=>[ent.id,ent]));for(const ent of dat.entries)if(!manual.has(ent.id))mapa.set(ent.id,{...ent,name:ent.name||ent.id});
      ents=Array.from(mapa.values());filtros();pinta();nodo('catalog-live-status').textContent='Catálogo leído; se conservan las decisiones manuales.';
    }catch(exc){nodo('catalog-live-status').textContent=exc.message+' La selección anterior se conserva.';}});
    for(const key of ['ram_budget_gib','ssd_budget_gib','preset_ram_gib','preset_ssd_gib']){nodo('capacity-'+key).value=dat_app.capacity_defaults[key];nodo('capacity-'+key).addEventListener('input',capacity);}
    nodo('capacity-ssd_mode').addEventListener('change',capacity);
    nodo('board-head').replaceChildren(window.AUXBoard.header(dat_app.status));
    nodo('status-export').addEventListener('click',()=>guarda('catalog.json',JSON.stringify(window.AUXCatalog.document(ents.map(e=>elegidos.get(e.id)||e)),null,2)+'\n','application/json'));
    nodo('status-snapshot').addEventListener('click',()=>guarda('status-public.json',JSON.stringify(dat_app.status,null,2)+'\n','application/json'));
    nodo('status-import').addEventListener('change',async evt=>{try{const f=evt.target.files[0];if(!f||f.size>2097152)throw Error('Elegir una instantánea JSON de hasta 2 MiB.');window.AUXBoard.importSnapshot(JSON.parse(await f.text()),ents,dat_app.status);pinta();aviso('Observaciones cargadas; P y CDE se conservan.');}catch(e){aviso(e.message);}});
    for(const button of document.querySelectorAll('[data-board-task]'))button.addEventListener('click',()=>{if(!elegidos.size){aviso('Elegir recursos y descargar la selección.');return;}const task=button.dataset.boardTask,cmd='./aux '+task+' --catalog catalog.json';nodo('workflow-command').textContent=cmd+' --dry-run\n'+cmd+(task==='checkstatus'?'':' --apply');});
    const audit=dat_app.status.audit||{};nodo('audit-summary').textContent=audit.checked_at?'Revisión HTTP: '+audit.checked_at+' · '+(audit.summary?.verified||0)+' URL comprobadas · revisión semanal.':'Sin auditoría HTTP publicada.';
    try{const saved=JSON.parse(sessionStorage.getItem(storageKey)||'null');if(saved){for(const edit of saved.entries||[]){const e=ents.find(e=>e.id===edit.id&&e.identity===edit.identity);if(e&&/^[0-9A-F]{3}$/.test(edit.policy)&&/^[0-9A-F]$/.test(edit.priority)&&(!e.remote_only||!(parseInt(edit.policy,16)&11)))Object.assign(e,{policy:edit.policy,priority:edit.priority});}for(const id of saved.selected||[]){const e=ents.find(e=>e.id===id);if(e)elegidos.set(id,{...e});}for(const id of saved.manual||[])manual.add(id);for(const id of saved.automatic||[])automaticos.add(id);for(const box of cajas)box.checked=box.value==='todos'?(saved.presets||[]).length===3:(saved.presets||[]).includes(box.value);}}catch{}restoring=false;
    nodo('catalog-search').value=new URLSearchParams(location.search).get('q')||'';filtros();pinta();
  }
  if(document.body.dataset.app==='adapt')nodo('evolve-export').addEventListener('click',()=>{
    const goal=nodo('evolve-goal').value.trim(),max=Number(nodo('evolve-tokens').value);if(!goal||!Number.isInteger(max)||max<512||max>16384){aviso('Describir el objetivo y revisar Max tokens.');return;}
    guarda('aux-adaptation-request.json',JSON.stringify({schema:'aux-adaptation-brief-v1',version:dat_app.version,goal,provider:nodo('evolve-provider').value,model:nodo('evolve-model').value.trim(),max_tokens:max,products:{recipes:dat_app.products.recipes.map(e=>e.id),policy:'CDE',status:'PASCDE; 24 visible bits; A/S observed'},next_step:'./aux self-assamble --request aux-adaptation-request.json --interactive'},null,2)+'\n','application/json');
  });
  if(document.body.dataset.app==='systems')nodo('open-cockpit').addEventListener('click',()=>{
    const url=url_valida(nodo('cockpit-url').value);if(!url||!url.startsWith('https://')){nodo('cockpit-status').textContent='Indicar la dirección HTTPS del equipo de destino.';return;}
    window.open(url,'_blank','noopener,noreferrer');
  });
})();
