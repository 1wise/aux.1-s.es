# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Forecast physical image copies separately from extracted deployment trees."""
from .catalog_v8 import acciones,presets

GIB=1024**3
DEFAULTS={'ram_budget_gib':30,'ssd_budget_gib':225,'ram_reserve_percent':0,
          'preset_ram_gib':10,'preset_ssd_gib':75,'ssd_mode':'extract'}


def options(cfg):
    return {**DEFAULTS,**{k:cfg[k] for k in DEFAULTS if k in cfg},
            **{k:cfg.get('presets',{})[k] for k in ('preset_ram_gib','preset_ssd_gib') if k in cfg.get('presets',{})}}


def prevision(entries,cfg,selected=(),mode=None):
    opt=options(cfg);sel=set(selected or []);sel.discard('todos')
    if 'todos' in (selected or []):sel={'alpine','fedora','debian'}
    for key in ('ram_budget_gib','ssd_budget_gib','preset_ram_gib','preset_ssd_gib'):
        if type(opt[key]) not in (int,float) or not 0<opt[key]<=1048576:raise ValueError('Presupuesto inválido: '+key)
    if type(opt['ram_reserve_percent']) not in (int,float) or not 0<=opt['ram_reserve_percent']<100:raise ValueError('Reserva RAM inválida.')
    physical={'ram':int(opt['ram_budget_gib']*GIB*(1-opt['ram_reserve_percent']/100)),
              'ssd':int(opt['ssd_budget_gib']*GIB),'bastion':int(opt['ssd_budget_gib']*GIB)}
    nominal={'ram':int(len(sel)*opt['preset_ram_gib']*GIB),'ssd':int(len(sel)*opt['preset_ssd_gib']*GIB),'bastion':int(len(sel)*opt['preset_ssd_gib']*GIB)} if sel else dict(physical)
    limits={k:min(physical[k],nominal[k]) for k in physical}
    images={k:0 for k in physical};deploys=dict(images);cache=dict(images);shared=dict(images);unknown=[];estimated=[];seen=set()
    for ent in entries:
        if ent['id'] in seen:continue
        seen.add(ent['id']);act=acciones(ent['policy']);loc=set(act['locations'])&set(physical)
        if not loc and not (act['download'] or act['update']):continue
        if ent.get('remote_only'):continue
        size=ent.get('size_bytes');cost=dict(images)
        if not size:
            unknown.append(ent['id']);continue
        cost={k:0 for k in physical}
        # One persistent acquisition feeds any number of destination copies.
        if act['download'] or act['update'] or loc:
            images['ssd']+=size;cache['ssd']+=size;cost['ssd']+=size
        for dest in loc:
            iso=ent.get('artifact_type')=='iso';mounted=iso and dest=='ssd' and (mode or opt['ssd_mode'])=='mount'
            if not mounted:images[dest]+=size;cost[dest]+=size
            if iso and dest=='ssd' and not mounted:
                extra=ent.get('deployment_size_bytes')
                if extra is None:extra=size;estimated.append(ent['id'])
                deploys[dest]+=extra;cost[dest]+=extra
        repetitions=max(0,len(sel&set(presets(ent)))-1)
        for dest in physical:shared[dest]+=cost[dest]*repetitions
    totals={k:images[k]+deploys[k] for k in physical}
    return {'schema':'aux-capacity-v1','units':'GiB','presets':sorted(sel),'images_bytes':images,
            'cache_bytes':cache,'deploy_bytes':deploys,'selected_bytes':totals,'budget_bytes':limits,
            'physical_budget_bytes':physical,'preset_budget_bytes':nominal,'shared_savings_bytes':shared,
            'remaining_bytes':{k:limits[k]-totals[k] for k in totals},'unknown_sizes':unknown,
            'estimated_deployments':estimated,'over_budget':[k for k in totals if totals[k]>limits[k]],
            'note':'SSD includes the source cache and physical public copies. Extracted ISO trees use an explicit size or an estimate equal to image size. RAM ISO mounts add no extracted copy. Bastion receives image files.'}


def resumen(dat):
    lines=['Destino | Imágenes (caché incluida) | Deploys | Total / límite (GiB)']
    for k in ('ram','ssd','bastion'):
        lines.append(f"{k.upper():7} | {dat['images_bytes'][k]/GIB:.2f} | {dat['deploy_bytes'][k]/GIB:.2f} | {dat['selected_bytes'][k]/GIB:.2f} / {dat['budget_bytes'][k]/GIB:.2f} · margen {dat['remaining_bytes'][k]/GIB:.2f}")
    lines+=['Compartidos: '+', '.join(k+' '+f"{v/GIB:.2f} GiB" for k,v in dat['shared_savings_bytes'].items()),
            'Tamaños pendientes: '+str(len(dat['unknown_sizes']))+'; deploys estimados: '+str(len(dat['estimated_deployments']))]
    if dat['over_budget']:lines.append('EXCEDIDO: '+', '.join(dat['over_budget']))
    return lines


def propuesta(entries,cfg,selected,base=()):
    """Fill a shared preset pool; preserve explicit choices and defer excess to origin."""
    sel=set(selected);sel={'alpine','fedora','debian'} if 'todos' in sel else sel
    result={e['id']:dict(e) for e in base};deferred=[]
    candidates=[e for e in entries if sel&set(presets(e))]
    def priority(e):
        from .policy24 import orden_prioridad
        return (*orden_prioridad(e,sel),0 if e.get('deploy_method')=='chroot' else 1 if e.get('recipe',{}).get('approved') else
                2 if e.get('download_class')!='heavy' else 3,
                0 if e.get('architecture') in ('x86_64','amd64') else 1,e.get('size_bytes') or 0,e['id'])
    for ent in sorted(candidates,key=priority):
        if ent['id'] in result:continue
        common=ent.get('deploy_method')=='chroot'
        key='origin_policy_bits' if ent.get('remote_only') else 'heavy_policy_bits' if ent.get('download_class')=='heavy' or common else 'light_policy_bits'
        mask=int(cfg.get('presets',{}).get(key,{'origin_policy_bits':'004','heavy_policy_bits':'016','light_policy_bits':'015'}[key]),16)
        copy={**ent,'policy':f"{int(ent['policy'],16)|mask:03X}"}
        forecast=prevision([*result.values(),copy],cfg,sel)
        if forecast['over_budget'] and not ent.get('remote_only') and not (int(ent.get('priority','0'),16)&4):
            copy['policy']=f"{(int(ent['policy'],16)&~0x3b)|4:03X}";deferred.append(ent['id'])
        result[ent['id']]=copy
    return list(result.values()),deferred
