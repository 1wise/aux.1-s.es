# Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
# Author & Credits: https://www.alawise.es/1-s
"""Show operational hazards and keep free capacity before privileged writes."""
from pathlib import Path
import shutil

GIB=1024**3
NOTAS={
 'remote':('RED TEAM / RED ROBIN · Control remoto','AUX Assist, SSH, Cockpit y gateways pueden exponer terminales o administración. Verificar destino, cuenta, puertos, firewall/VPN, consentimiento y cómo cerrar la sesión. Instalar no autoriza una intervención.'),
 'writes':('RED TEAM / RED ROBIN · Escrituras persistentes','Instalar, desplegar, grabar USB o cambiar montajes puede modificar datos y arranque. Revisar ruta, dispositivo, copias y espacio libre antes de aplicar.'),
 'load':('RED TEAM / RED ROBIN · Carga y cuotas','Los presets son propuestas para un equipo de referencia. RAM, tmpfs, caché, extracción, hashes y descargas concurrentes compiten con los procesos existentes. Una cuota nominal no reserva recursos ni limita por sí sola CPU, I/O o servicios permanentes.'),
}


def lineas(*claves):
    return [titulo+'\n'+texto for titulo,texto in (NOTAS[k] for k in claves)]


def html(clave):
    titulo,txt=NOTAS[clave]
    return '<aside class="red-robin" role="note"><img src="assets/red-robin.webp" alt="Red Robin: precaución" width="48" height="48"><div><strong>'+titulo+'</strong><p>'+txt+'</p><a href="precautions.html">Precauciones y cierre de la intervención</a></div></aside>'


def meminfo(pth='/proc/meminfo'):
    return {l.split(':',1)[0]:int(l.split()[1])*1024 for l in Path(pth).read_text().splitlines() if l.startswith(('MemTotal:','MemAvailable:'))}


def espacio(pth):
    pth=Path(pth)
    while not pth.exists():pth=pth.parent
    return shutil.disk_usage(pth).free


def protege(destino,necesario,ram=False):
    if necesario is None or necesario<0:raise ValueError('RED ROBIN: resolver el tamaño antes de escribir.')
    if ram:
        mem=meminfo();reserva=max(512*1024**2,mem['MemTotal']//5);libre=mem['MemAvailable']
    else:reserva=GIB;libre=espacio(destino)
    if necesario>max(0,libre-reserva):
        raise ValueError('RED ROBIN: capacidad disponible insuficiente; se conserva una reserva para el sistema. Reducir la selección o elegir otro destino.')
    return {'available_bytes':libre,'reserve_bytes':reserva,'requested_bytes':necesario}


def guia():
    from . import VERSION
    blue='<aside class="blue-hibou"><img src="assets/blue-hibou.svg" alt="Blue Hibou: guía de despliegue" width="64" height="64"><div><strong>Blue Hibou · Despliegue rápido</strong><p>Elegir recursos, revisar el plan, desplegar y comprobar. Una guía de despliegue no sustituye las precauciones del equipo concreto.</p></div></aside>'
    return '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AUX · Blue Hibou y Red Robin</title><link rel="stylesheet" href="assets/workspace.css"><body><header class="app-header"><a href="workspace.html">./aux '+VERSION+'</a> · <a href="status.html">Tablero de estado</a> · <a href="installer.html">Instalar</a></header><main><h1>Blue Hibou y Red Robin</h1>'+blue+''.join(html(k) for k in NOTAS)+'<h2>Antes, durante y después</h2><ol><li>Revisar hostname, destino, cuenta y recursos que ya consume el equipo.</li><li>Activar solo los componentes necesarios. AUX Assist y administración con Cockpit son opcionales.</li><li>Comprobar puertos, sockets y servicios después de instalar paquetes: la distribución puede activarlos.</li><li>Conservar una reserva para el sistema; reducir concurrencia y evitar cargas permanentes sin supervisión.</li><li>Al terminar, cerrar la sesión de asistencia, revisar procesos, montajes, sockets y tareas programadas; confirmar que los accesos temporales han terminado.</li></ol><p>Los límites del catálogo son previsiones. Las comprobaciones de memoria y espacio ayudan a detener una escritura nueva; no limitan por sí solas CPU, I/O, otros procesos o crecimiento posterior.</p><p><a href="downloads/docs/RED-ROBIN-8.md">Guía completa de precauciones</a> · <a href="downloads/docs/MATRIOSHKA-8.0.1.md">Despliegue de las cuatro entregas</a></p></main></body></html>'
