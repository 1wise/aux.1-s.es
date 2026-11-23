# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Identify the exact edition and architecture even in reports from older versions."""
from urllib.parse import unquote,urlsplit


def identidad(fila, config):
    slot = next((s for s in config.get('download_slots',[]) if s['id']==fila.get('slot_id')), {})
    actual = fila.get('original_url')
    previo = fila.get('previous_url','')
    archivo = unquote(urlsplit(actual or previo).path).rstrip('/').removesuffix('/download').rsplit('/',1)[-1]
    nombre = slot.get('label',fila.get('name','Recurso')).split(' / ')[0]
    if archivo.startswith('Fedora-'):
        nombre = 'Fedora '+archivo.split('-')[1]
        if '-Live-' in archivo: nombre += ' Live'
        elif '-netinst-' in archivo: nombre += ' netinst'
    arq = fila.get('architecture') or slot.get('architecture') or '?'
    version = str(fila.get('release') or 'por resolver')
    return nombre,arq,version,archivo,bool(actual)


def rotulo(fila, config):
    nombre,arq,version,_,_ = identidad(fila,config)
    est = 'disponible con avisos' if fila.get('http',{}).get('http')=='passed' else 'pendiente'
    return ' | '.join([nombre,arq,version,est,fila.get('slot_id','sin regla')])


def detalles(fila, config):
    nombre,arq,version,archivo,actual = identidad(fila,config)
    return ['Imagen: '+nombre,'Arquitectura: '+arq,'Versión resuelta: '+version,
            ('Archivo actual: ' if actual else 'Archivo de la lista anterior: ')+archivo,
            'Canal: '+str(fila.get('channel','?')),'Regla: '+str(fila.get('slot_id','sin regla')),
            'HTTP: '+str(fila.get('http',{}).get('http','sin comprobar')),
            'URL: '+str(fila.get('original_url') or fila.get('previous_url')),
            'Motivo: '+str(fila.get('error') or fila.get('http',{}).get('error') or fila.get('source_warning') or
                           fila.get('unavailable_newer_versions') or 'Revisión solicitada')]
