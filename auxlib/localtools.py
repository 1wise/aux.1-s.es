# Timestamp: 2026-11-10 | Version: 7.0.0-beta.0
# Author & Credits: https://www.alawise.es/1-s
"""Shared entries for the physical console, desktop and standalone tools."""
import argparse
import curses
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

from . import VERSION
from .common import DIR_APP, guarda_json
from .interactive import elige
from .console_ui import aplicacion


def abre(nom):
    if nom=='images':
        return subprocess.run([sys.executable,str(DIR_APP/'aux-images'),'--interactive'],check=False).returncode
    if nom in ('installer','systems'):
        exe='aux-setup' if nom=='installer' else 'aux-enter'
        return subprocess.run([sys.executable,str(DIR_APP/exe),'--interactive'],check=False).returncode
    if nom=='cockpit':
        if input('Iniciar Cockpit en este equipo [s/N]: ').strip().lower()=='s':
            subprocess.run(['systemctl','start','cockpit.socket'],check=True)
        rsp=subprocess.run(['hostname','-I'],capture_output=True,text=True,check=True)
        for ip in ['localhost']+rsp.stdout.split():
            print('https://'+('['+ip+']' if ':' in ip else ip)+':9090')
        print('Acceso con una cuenta del sistema de destino.')
        input('Enter para volver: ')
        return 0
    if nom=='catalogue':
        return catalogo()
    if nom=='gui':
        pth=Path('/usr/local/share/aux/workspace.html')
        if not pth.is_file():
            raise ValueError('Instalar las aplicaciones AUX antes de abrir el escritorio.')
        return subprocess.run(['xdg-open',pth.as_uri()],check=False).returncode
    raise ValueError('Aplicación desconocida.')


def catalogo():
    from .webapps import modelo
    pth=Path('/srv/aux/catalog/current/catalog.json')
    ents=json.loads(pth.read_text())['entries'] if pth.is_file() else modelo()['entries']
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('El selector necesita una terminal interactiva con soporte curses.')
    sel=curses.wrapper(seleccion_catalogo,ents)
    from .catalog_selection import cabe_catalogo, limites_catalogo
    if not cabe_catalogo(sel,limites_catalogo()):
        raise ValueError('La selección supera los límites o contiene tamaños locales desconocidos.')
    if not sel:
        print('Selección cancelada o vacía.')
        return 0
    nom=input('Directorio nuevo para los archivos [./aux-seleccion]: ').strip() or './aux-seleccion'
    destino=Path(nom).expanduser().absolute()
    if destino.exists() or destino.is_symlink():
        raise ValueError('El destino ya existe; elegir un directorio nuevo.')
    if not destino.parent.is_dir():
        raise ValueError('El directorio padre no existe.')
    with tempfile.TemporaryDirectory(prefix='.aux-selection-',dir=destino.parent) as tmp:
        raiz=Path(tmp)
        guarda_json(raiz/'aux-catalog-selection.json',{'metadata':{'version':VERSION,'preset':getattr(sel,'preset','custom'),
                    'limits':getattr(sel,'limites',limites_catalogo())},'entries':sel})
        for clase in ('light','heavy'):
            (raiz/(clase+'-url.txt')).write_text(''.join(ent['original_url']+'\n' for ent in sel if ent['download_class']==clase and not ent.get('remote_only') and ent.get('selection_mode')!='origin'))
        (raiz/'origin-url.txt').write_text(''.join(ent['original_url']+'\n' for ent in sel if ent.get('remote_only') or ent.get('selection_mode')=='origin'))
        if destino.exists() or destino.is_symlink():
            raise ValueError('El destino ya existe; se conserva.')
        os.rename(raiz,destino)
    print('Selección y listas de origen guardadas en:',destino)
    print('La selección no descarga imágenes; la publicación local requiere límites explícitos.')
    return 0


def tamano(ent):
    val=ent.get('size_bytes',ent.get('size'))
    return val if isinstance(val,int) and not isinstance(val,bool) and val>0 else None


def resumen_catalogo(ents):
    sal={clase:{'bytes':0,'unknown':0,'count':0} for clase in ('light','heavy')}
    for ent in ents:
        if ent.get('remote_only') or ent.get('selection_mode')=='origin':
            continue
        clase=ent.get('download_class')
        if clase not in sal:
            raise ValueError('Clasificación light/heavy inválida.')
        dat=sal[clase];dat['count']+=1
        val=tamano(ent)
        if val is None: dat['unknown']+=1
        else: dat['bytes']+=val
    return sal


def memoria_catalogo():
    cfg=json.loads((DIR_APP/'fast-boot.json').read_text())
    presupuesto=int(float(cfg.get('ram_budget_gib',22))*1024**3)
    reserva=float(cfg.get('ram_reserve_percent',10))
    if presupuesto<=0 or not 0<=reserva<100:
        raise ValueError('Presupuesto o reserva de RAM inválidos en fast-boot.json.')
    disponible=None
    try:
        for lin in Path('/proc/meminfo').read_text().splitlines():
            if lin.startswith('MemAvailable:'):
                disponible=int(lin.split()[1])*1024
                break
    except (OSError,ValueError,IndexError):
        pass
    libre=None
    destino=Path(cfg.get('cache','/var/www/aux.1-s.es/isos'))
    try:
        datos=os.statvfs(destino)
        libre=datos.f_bavail*datos.f_frsize
    except OSError:
        pass
    return int(presupuesto*(1-reserva/100)),disponible,libre


def muestra_origen(scr, ent):
    """Allow the full upstream URL to be read, including on narrow terminals."""
    inicio=0
    while True:
        h,w=scr.getmaxyx();scr.erase()
        lineas=textwrap.wrap(str(ent.get('original_url','')),width=max(1,w-2),break_long_words=True,break_on_hyphens=False) or ['Sin URL de origen']
        alto=max(1,h-3);inicio=max(0,min(inicio,max(0,len(lineas)-alto)))
        try:
            scr.addnstr(0,0,'AUX CATALOG | URL de origen · flechas para desplazar · Enter para volver',max(0,w-1))
            for idx,lin in enumerate(lineas[inicio:inicio+alto],1):scr.addnstr(idx,0,lin,max(0,w-1))
        except curses.error: pass
        scr.refresh();tecla=scr.get_wch()
        if tecla in ('\n','\r',curses.KEY_ENTER,'q','Q','\x1b'): return
        if tecla==curses.KEY_DOWN: inicio+=1
        if tecla==curses.KEY_UP: inicio-=1


CATEGORIAS_TOOLS = {
    'Discos y recuperación': {'clonezilla','gparted','systemrescue','rescatux','supergrub','testdisk','partedmagic'},
    'Diagnóstico y memoria': {'memtest','memtest86','memtest86+','hwinfo','diagnostics'},
    'Seguridad y análisis': {'dban','shredos','ophcrack','antivirus','security'},
    'Arranque y red': {'netboot','ipxe','grub','plop','netbootxyz'},
}


def arbol_catalogo(entradas):
    """Group each upstream entry once, keeping unmatched resources discoverable."""
    distribuciones={};herramientas={}
    for ent in entradas:
        familia=str(ent.get('family') or 'otras').strip().lower()
        tipo=str(ent.get('kind') or '').lower()
        categoria=next((nom for nom,ids in CATEGORIAS_TOOLS.items() if familia in ids),None)
        if not categoria and familia.startswith('utilities'):
            categoria='Arranque y red'
        if categoria or tipo in ('tool','netboot-utility'):
            herramientas.setdefault(categoria or 'Otras herramientas',[]).append(ent)
        else:
            distribuciones.setdefault(familia,[]).append(ent)
    return distribuciones,herramientas


def colores_catalogo(scr):
    from .console_ui import paleta
    return paleta(scr, 'configuracion')


def elige_modo_catalogo(scr, ent, estilos):
    """Choose where an entry is deployed without changing upstream metadata."""
    opciones=[('Light: archivos ligeros','light'),('Heavy: imagen completa','heavy'),
              ('Solo origen: enlace externo','origin')]
    if ent.get('remote_only'):
        opciones=opciones[2:]
    actual=ent.get('selection_mode') or ent.get('download_class','light')
    pos=next((n for n,(_,val) in enumerate(opciones) if val==actual),0)
    while True:
        h,w=scr.getmaxyx();scr.erase()
        def texto(y,txt,atr):
            if 0<=y<h:
                try: scr.addnstr(y,2,txt,max(0,w-4),atr)
                except curses.error: pass
        texto(0,'AUX CATALOG | MODO DE DESPLIEGUE',estilos['titulo'])
        texto(2,str(ent.get('name') or ent.get('family','')),estilos['detalle'])
        texto(3,'Flechas: elegir   Enter: aceptar   Esc: volver',estilos['ayuda'])
        for n,(nom,val) in enumerate(opciones):
            texto(5+n,('(*) ' if val==actual else '( ) ')+nom,
                  estilos['activo'] if n==pos else estilos['normal'])
        scr.refresh();tecla=scr.get_wch()
        if tecla in ('\x1b',curses.KEY_BACKSPACE,127,'\b','q','Q'): return
        if tecla in (curses.KEY_DOWN,'j'): pos=min(pos+1,len(opciones)-1)
        elif tecla in (curses.KEY_UP,'k'): pos=max(0,pos-1)
        elif tecla in ('\n','\r',curses.KEY_ENTER,' '):
            modo=opciones[pos][1];ent['selection_mode']=modo
            if modo in ('light','heavy'): ent['download_class']=modo
            return


def seleccion_catalogo(scr, entradas):
    """Keep available resources and the bounded selection in separate panels."""
    from .catalog_selection import (limites_catalogo, preset_catalogo, uso_catalogo,
                                    modo_catalogo, incorpora_catalogo, SeleccionCatalogo)
    originales=[dict(e) for e in entradas];ents=[dict(e) for e in entradas]
    limites=limites_catalogo();preset='default';personal={}
    seleccion=preset_catalogo(originales,preset,limites)
    for ent in ents:
        if ent['id'] in seleccion:ent.update(seleccion[ent['id']])
    ruta=[];bus='';pos=0;pos_sel=0;panel=0;inicio=0;aviso=''
    distribuciones,herramientas=arbol_catalogo(ents)
    scr.keypad(True);estilos=colores_catalogo(scr)

    def texto(y,x,txt,ancho,estilo='normal'):
        h,w=scr.getmaxyx()
        if 0<=y<h and x<w:
            try:scr.addnstr(y,x,txt,max(0,min(ancho,w-x-1)),estilos[estilo])
            except curses.error:pass

    def conserva_custom():
        nonlocal preset,personal
        preset='custom';personal={k:dict(v) for k,v in seleccion.items()}

    def carga_preset():
        nonlocal seleccion,preset,pos_sel,aviso
        noms=[('default','Default · listas AUX actuales'),
              ('suggested','Sugerido · instalación y rescate'),('custom','Custom · selección manual')]
        idx=next(n for n,(val,_) in enumerate(noms) if val==preset)
        while True:
            h,w=scr.getmaxyx();scr.erase()
            texto(0,2,'AUX | PRESETS',w-4,'titulo')
            for n,(_,nom) in enumerate(noms):texto(3+n,2,nom,w-4,'activo' if n==idx else 'normal')
            texto(8,2,'Enter: aplicar   Esc: volver',w-4,'ayuda')
            scr.refresh();tecla=scr.get_wch()
            if tecla in ('\x1b','q','Q',curses.KEY_BACKSPACE):return
            if tecla in (curses.KEY_DOWN,'j'):idx=min(2,idx+1)
            elif tecla in (curses.KEY_UP,'k'):idx=max(0,idx-1)
            elif tecla in ('\n','\r',curses.KEY_ENTER):
                preset=noms[idx][0]
                seleccion=({k:dict(v) for k,v in personal.items()} if preset=='custom'
                           else preset_catalogo(originales,preset,limites))
                for ent,orig in zip(ents,originales):
                    ent.clear();ent.update(orig)
                    if ent['id'] in seleccion:ent.update(seleccion[ent['id']])
                pos_sel=0;aviso='Preset aplicado; sin tamaño o espacio queda solo origen.'
                return

    while True:
        h,w=scr.getmaxyx();scr.erase()
        if h<18 or w<100:
            texto(0,0,'Ampliar terminal a 100 columnas x 18 filas; Q cancela.',w)
            scr.refresh()
            if scr.get_wch() in ('q','Q','\x1b'):return []
            continue
        if not ruta:
            items=[('Distribuciones','menu','distribuciones'),('Herramientas por categoría','menu','herramientas'),
                   ('Todas las entradas','menu','todos'),('Selección actual','menu','seleccionados')]
        elif ruta[0] in ('distribuciones','herramientas') and len(ruta)==1:
            grupos=distribuciones if ruta[0]=='distribuciones' else herramientas
            items=[(nom+' ('+str(len(vals))+')','menu',nom) for nom,vals in sorted(grupos.items(),key=lambda e:e[0].casefold())]
        else:
            if ruta[0]=='distribuciones':lista=distribuciones[ruta[1]]
            elif ruta[0]=='herramientas':lista=herramientas[ruta[1]]
            elif ruta[0]=='seleccionados':lista=[e for e in ents if e['id'] in seleccion]
            else:lista=ents
            if bus:lista=[e for e in lista if bus.casefold() in ' '.join(str(e.get(k,'')) for k in ('name','family','release','architecture','original_url')).casefold()]
            items=[('', 'entry',e) for e in lista]
        pos=max(0,min(pos,len(items)-1));alto=h-10;mitad=w//2
        if pos<inicio:inicio=pos
        if pos>=inicio+alto:inicio=pos-alto+1
        sel=[seleccion[e['id']] for e in ents if e['id'] in seleccion]
        pos_sel=max(0,min(pos_sel,len(sel)-1));uso=uso_catalogo(sel);tot=resumen_catalogo(sel)
        texto(0,0,'AUX CATALOG '+VERSION+' | MENUCONFIG | Preset: '+preset,w,'titulo')
        texto(1,0,' / '.join(ruta) or 'MENU PRINCIPAL',w,'detalle')
        texto(2,0,('> ' if panel==0 else '  ')+'DISPONIBLES',mitad-1,'titulo')
        texto(2,mitad,('> ' if panel==1 else '  ')+'SELECCIONADAS ('+str(len(sel))+')',w-mitad,'titulo')
        for y in range(3,h-7):texto(y,mitad-1,'|',1,'detalle')
        def rotulo(ent):
            modo=modo_catalogo(ent);peso=tamano(ent)
            tam=f'{peso/1024**3:.2f}G' if peso else '?G'
            return modo.upper()[:1]+' '+tam.rjust(6)+' '+str(ent.get('architecture',''))[:8].ljust(8)+' '+str(ent.get('release',''))[:6].ljust(6)+' '+str(ent.get('name') or ent.get('family',''))
        for idx,(nom,tipo,ent) in enumerate(items[inicio:inicio+alto],inicio):
            txt=nom+' --->' if tipo!='entry' else ('[x] ' if ent['id'] in seleccion else '[ ] ')+rotulo(ent)
            texto(3+idx-inicio,0,txt,mitad-2,'activo' if panel==0 and idx==pos else 'normal')
        inicio_sel=max(0,pos_sel-alto+1)
        for idx,ent in enumerate(sel[inicio_sel:inicio_sel+alto],inicio_sel):
            texto(3+idx-inicio_sel,mitad,rotulo(ent),w-mitad,'activo' if panel==1 and idx==pos_sel else 'normal')
        texto(h-7,0,'LIGHT '+str(tot['light']['count'])+' | RAM '+f"{uso['ram']/1024**3:.2f}/{limites['ram']/1024**3:.2f} GiB útiles (reserva aplicada)",w,'detalle')
        texto(h-6,0,'HEAVY '+str(tot['heavy']['count'])+' | SSD '+f"{uso['ssd']/1024**3:.2f}/{limites['ssd']/1024**3:.2f} GiB (incluye light) | ORIGEN "+str(sum(modo_catalogo(e)=='origin' for e in sel)),w,'detalle')
        actual=(sel[pos_sel] if sel else None) if panel else (items[pos][2] if items and items[pos][1]=='entry' else None)
        texto(h-5,0,'Origen: '+str(actual.get('original_url','')) if actual else 'Enter: abrir submenú. Tab: cambiar panel.',w)
        texto(h-4,0,aviso or 'Tamaños de archivo; expansión y RAM de ejecución adicionales. ?G = sin tamaño.',w,'detalle')
        texto(h-3,0,'Enter: menú/modo | Espacio: marcar/quitar | Tab: panel | A: seleccionar todo | P: presets',w,'ayuda')
        texto(h-2,0,'L/H/R: light/heavy/origen | O: ver URL | /: buscar | Retroceso: volver | S: guardar | Q: salir',w,'ayuda')
        texto(h-1,0,'Seleccionar todo: grupo/lista visible; desde el menú principal: catálogo completo.',w,'ayuda')
        scr.refresh();tecla=scr.get_wch()
        if tecla in ('q','Q'):return []
        if tecla in ('s','S',curses.KEY_F10):return SeleccionCatalogo(sel,preset,limites)
        if tecla=='\t':panel=1-panel;continue
        if tecla in ('p','P'):carga_preset();continue
        if tecla in ('a','A') and panel==0:
            if not ruta:candidatos=ents
            elif len(ruta)==1 and ruta[0] in ('distribuciones','herramientas'):
                grupos=distribuciones if ruta[0]=='distribuciones' else herramientas
                candidatos=[e for vals in grupos.values() for e in vals]
            else:candidatos=[e for _,tipo,e in items if tipo=='entry']
            razones={'sin tamaño':0,'sin espacio':0}
            for ent in candidatos:
                if ent['id'] in seleccion:continue
                razon=incorpora_catalogo(ent,seleccion,limites)
                if razon:razones[razon]+=1
                ent.update(seleccion[ent['id']])
            conserva_custom();aviso='Añadidas '+str(len(candidatos))+' opciones; solo origen: '+str(razones['sin tamaño'])+' sin tamaño, '+str(razones['sin espacio'])+' sin espacio.'
            continue
        if tecla in ('\x1b',curses.KEY_BACKSPACE,127,'\b'):
            if panel:panel=0
            elif ruta:ruta.pop();bus='';pos=0;inicio=0
            else:return []
        elif tecla in (curses.KEY_DOWN,'j',curses.KEY_UP,'k',curses.KEY_NPAGE,curses.KEY_PPAGE):
            paso=alto if tecla in (curses.KEY_NPAGE,curses.KEY_PPAGE) else 1
            if tecla in (curses.KEY_UP,'k',curses.KEY_PPAGE):paso=-paso
            if panel:pos_sel=max(0,min(pos_sel+paso,len(sel)-1))
            else:pos=max(0,min(pos+paso,len(items)-1))
        elif tecla in ('\n','\r',curses.KEY_ENTER) and panel==0 and items and items[pos][1]=='menu':
            ruta.append(items[pos][2]);bus='';pos=0;inicio=0
        elif tecla==' ' and actual:
            if actual['id'] in seleccion:seleccion.pop(actual['id'])
            else:
                razon=incorpora_catalogo(actual,seleccion,limites);actual.update(seleccion[actual['id']])
                aviso='Solo origen: '+razon if razon else ''
            conserva_custom()
        elif actual and tecla in ('\n','\r',curses.KEY_ENTER,'l','L','h','H','r','R'):
            copia=dict(actual)
            if tecla in ('\n','\r',curses.KEY_ENTER):elige_modo_catalogo(scr,copia,estilos)
            else:
                modo={'l':'light','h':'heavy','r':'origin'}[tecla.lower()]
                if copia.get('remote_only') and modo!='origin':continue
                copia['selection_mode']=modo
                if modo!='origin':copia['download_class']=modo
            temporal=dict(seleccion)
            razon=incorpora_catalogo(copia,temporal,limites)
            actual.update(temporal[actual['id']])
            if actual['id'] in seleccion:seleccion[actual['id']]=dict(actual)
            aviso='Solo origen: '+razon if razon else ''
            conserva_custom()
        elif tecla in ('o','O') and actual:muestra_origen(scr,actual)
        elif tecla=='/' and not panel:
            if not ruta or len(ruta)==1 and ruta[0] in ('distribuciones','herramientas'):ruta=['todos']
            texto(h-1,0,'Buscar: ',w,'ayuda');curses.echo()
            try:bus=scr.getstr(h-1,8,w-10).decode('utf-8','replace').strip()
            finally:curses.noecho()
            pos=0;inicio=0


@aplicacion('AUX TOOLS','configuracion')
def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--interactive',action='store_true')
    par.add_argument('--gui',action='store_true')
    par.add_argument('--tool',choices=('installer','catalogue','systems','cockpit'))
    cfg=par.parse_args(argv)
    if cfg.gui:
        return abre('gui')
    if cfg.tool:
        return abre(cfg.tool)
    nom=elige('AUX '+VERSION+' | APLICACIONES',[
        ('Instalar y personalizar','installer'),('Catálogo y selección','catalogue'),('Generar imágenes y perfiles','images'),
        ('Sistemas y chroot','systems'),('Cockpit del equipo','cockpit')])
    return abre(nom)
