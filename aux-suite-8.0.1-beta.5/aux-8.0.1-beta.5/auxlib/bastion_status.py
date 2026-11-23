# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Make remote inventory activation explicit and reuse existing connection settings."""
import copy
import getpass
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


def prueba_conexion(cfg, modo, config=None, secretos=None):
    from .settings import lee_secretos,ruta_secretos
    sec=lee_secretos(secretos,config)
    if modo=='rsync':
        from .ssh_auth import prueba
        return {'transport':'rsync','status':'ok','details':prueba(cfg,sec,config)}
    from .ftp_connection import prueba
    return {'transport':'ftps' if cfg.get('ftp_tls',True) else 'ftp',**prueba(cfg,sec)}


def cambia_raiz_ftp(cfg, raiz):
    from .checkstatus import _raiz
    cfg=copy.deepcopy(cfg);raiz=_raiz(raiz);anterior=cfg.get('ftp_root','/');cfg['ftp_root']=raiz
    est=valor(cfg,'checkstatus.bastion',{});ssh=valor(cfg,'mirror.remote_root')
    for ent in est.get('directories',[]):
        if est.get('transport') in ('ftp','ftps'):
            if len(est['directories'])==1 or ent['path']==anterior:ent['path']=raiz
        elif ssh and (ent['path']==ssh or ent['path'].startswith(ssh.rstrip('/')+'/')):
            ent['ftp_path']=_raiz(raiz.rstrip('/')+'/'+ent['path'][len(ssh):].lstrip('/'))
    return cfg


def explora_ftp(config=None, secretos=None):
    from .settings import lee_secretos
    from .ftp_connection import abre,listado
    from .console_ui import campo
    from .interactive import elige
    cfg=lee_config(config);conn=abre(cfg,lee_secretos(secretos,config))
    try:
        while True:
            pwd=conn.pwd();dirs=[n for n,f in listado(conn) if f.get('type')=='dir' and not n.startswith('.') and '/' not in n]
            opt=elige('FTP: '+pwd,[('Usar este directorio como raíz pública','use'),('Subir un nivel','up'),
                *[(n+'/',('dir',n)) for n in dirs],('Volver sin guardar','back')])
            if opt=='back':return
            if opt=='up':conn.cwd('..');continue
            if isinstance(opt,tuple):conn.cwd(opt[1]);continue
            nuevo=cambia_raiz_ftp(cfg,pwd)
            resumen=['Raíz FTP: '+pwd,*[json.dumps(e,ensure_ascii=False) for e in valor(nuevo,'checkstatus.bastion.directories',[])]]
            if campo('Escribir APLICAR para guardar la raíz FTP seleccionada',resumen=resumen)!='APLICAR':continue
            establece('ftp_root',pwd,config)
            if valor(nuevo,'checkstatus.bastion.directories'):establece('checkstatus.bastion.directories',json.dumps(nuevo['checkstatus']['bastion']['directories']),config)
            return
    finally:conn.close()


def configura(config=None, secretos=None):
    from .console_ui import campo
    from .interactive import elige
    fields = ['checkstatus.bastion.enabled','checkstatus.bastion.transport','checkstatus.bastion.directories',
              'checkstatus.bastion.fallback_ftp','checkstatus.timeout_seconds','mirror.ssh_auth']
    while True:
        cfg = lee_config(config)
        opt = elige(resumen(cfg),[
            ('Activar con el FTP/FTPS ya configurado','ftp'),
            ('Activar con el rsync/SSH ya configurado','rsync'),
            ('Contraseña SSH / rsync (entrada oculta)','ssh_password'),
            ('Contraseña FTP / FTPS (entrada oculta)','ftp_password'),
            ('Editar conexión SSH / rsync','ssh_fields'),('Editar conexión FTP / FTPS','ftp_fields'),
            ('Probar SSH / rsync','test_ssh'),('Probar FTP / FTPS','test_ftp'),
            ('Explorar FTP y elegir la raíz pública','browse_ftp'),
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
            elif opt in ('ssh_password','ftp_password'):
                from .settings import guarda_secreto
                clave=getpass.getpass(('Contraseña SSH / rsync' if opt=='ssh_password' else 'Contraseña FTP / FTPS')+' (entrada oculta; vacío elimina): ')
                guarda_secreto(opt,clave,secretos,config)
                if opt=='ssh_password' and clave:establece('mirror.ssh_auth','password',config)
            elif opt in ('test_ssh','test_ftp'):
                campo('Resultado de conexión; Enter vuelve a Bastion',resumen=json.dumps(prueba_conexion(cfg,'rsync' if opt=='test_ssh' else 'ftp',config,secretos),ensure_ascii=False,indent=2).splitlines())
            elif opt=='browse_ftp':explora_ftp(config,secretos)
            elif opt=='off':establece('checkstatus.bastion.enabled','false',config)
            elif opt in ('edit','ssh_fields','ftp_fields'):
                opciones=fields if opt=='edit' else ['mirror.ssh_host','mirror.ssh_user','mirror.ssh_port','mirror.remote_root','mirror.ssh_auth','mirror.ssh_identity','mirror.ssh_known_hosts'] if opt=='ssh_fields' else ['ftp_host','ftp_user','ftp_port','ftp_root','ftp_tls']
                key=elige('Ajuste de Bastion',[(f,f) for f in opciones]+[('Volver','back')])
                if key=='back':continue
                val=valor(cfg,key,True if key.endswith('fallback_ftp') else 'auto' if key.endswith('ssh_auth') else '')
                txt=json.dumps(val) if isinstance(val,(list,bool)) else str(val)
                establece(key,campo(key,txt,validar=lambda x:convierte(key,x)),config)
        except (ValueError,OSError) as exc:
            campo('Bastion pendiente; revisar la conexión en AUX Config',resumen=[str(exc)])
