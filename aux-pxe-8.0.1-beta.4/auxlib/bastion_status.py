# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Make remote inventory activation explicit and reuse existing connection settings."""
import copy
import json

from .settings import convierte, establece, lee_config, valor


def activa(cfg, transporte):
    from .checkstatus import _raiz
    from .catalog_v8 import url_publica
    cfg = copy.deepcopy(cfg)
    if transporte in ('ftp','ftps'):
        for key in ('ftp_host','ftp_user'):
            convierte(key,str(cfg.get(key) or ''))
        raiz = _raiz(cfg.get('ftp_root') or '/')
    elif transporte == 'rsync':
        for key in ('mirror.ssh_host','mirror.ssh_user'):
            convierte(key,str(valor(cfg,key) or ''))
        raiz = _raiz(valor(cfg,'mirror.remote_root') or '')
    else:
        raise ValueError('Seleccionar rsync, ftp o ftps.')
    url = valor(cfg,'targets.bastion.base_url') or cfg.get('download_url')
    url_publica(url)
    ent = {'path':raiz,'public_url':url}
    if transporte == 'rsync' and cfg.get('ftp_host') and cfg.get('ftp_user'):
        ent['ftp_path'] = _raiz(cfg.get('ftp_root') or '/')
    cfg.setdefault('checkstatus',{})['bastion'] = {
        **valor(cfg,'checkstatus.bastion',{}),'enabled':True,'transport':transporte,'directories':[ent]}
    return cfg


def resumen(cfg):
    est = valor(cfg,'checkstatus.bastion',{})
    return 'Bastion: '+('activo · '+est.get('transport','auto') if est.get('enabled') else 'desactivado · B para configurar')


def configura(config=None):
    from .console_ui import campo
    from .interactive import elige
    fields = ['checkstatus.bastion.enabled','checkstatus.bastion.transport','checkstatus.bastion.directories',
              'checkstatus.bastion.fallback_ftp','checkstatus.timeout_seconds','mirror.ssh_auth']
    while True:
        cfg = lee_config(config)
        opt = elige(resumen(cfg),[
            ('Activar con el FTP/FTPS ya configurado','ftp'),
            ('Activar con el rsync/SSH ya configurado','rsync'),
            ('Editar un ajuste del inventario','edit'),('Desactivar Bastion','off'),('Volver','back')])
        if opt == 'back':return
        try:
            if opt in ('ftp','rsync'):
                modo = ('ftps' if cfg.get('ftp_tls',True) else 'ftp') if opt=='ftp' else 'rsync'
                nuevo = activa(cfg,modo)['checkstatus']['bastion']
                detalles = ['Transporte: '+modo,*[e['path']+' = '+e['public_url'] for e in nuevo['directories']],
                            'Reutiliza la conexión y el almacén privado existentes. No transfiere archivos.']
                if campo('Escribir APLICAR para activar este inventario',resumen=detalles)!='APLICAR':continue
                for key in ('transport','directories','enabled'):
                    val = nuevo[key]
                    establece('checkstatus.bastion.'+key,json.dumps(val) if isinstance(val,(list,bool)) else val,config)
            elif opt=='off':establece('checkstatus.bastion.enabled','false',config)
            elif opt=='edit':
                key=elige('Ajuste de Bastion',[(f,f) for f in fields]+[('Volver','back')])
                if key=='back':continue
                val=valor(cfg,key,True if key.endswith('fallback_ftp') else 'auto' if key.endswith('ssh_auth') else '')
                txt=json.dumps(val) if isinstance(val,(list,bool)) else str(val)
                establece(key,campo(key,txt,validar=lambda x:convierte(key,x)),config)
        except (ValueError,OSError) as exc:
            campo('Bastion pendiente; revisar la conexión en AUX Config',resumen=[str(exc)])
