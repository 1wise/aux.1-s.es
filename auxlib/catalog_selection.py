# Timestamp: 2026-11-10 | Version: 7.0.0-beta.0
# Author & Credits: https://www.alawise.es/1-s
"""Plan catalogue selections against explicit payload budgets."""
import json
from .common import DIR_APP

GIB = 1024**3
PRESETS = ('default', 'suggested', 'custom')
RECOMENDADOS = ('rescatux', 'systemrescue', 'clonezilla', 'gparted', 'memtest',
                'supergrub', 'netboot', 'debian', 'fedora', 'alpine', 'arch',
                'ubuntu', 'proxmox')


class SeleccionCatalogo(list):
    def __init__(self, entradas, preset, limites):
        super().__init__(entradas)
        self.preset = preset
        self.limites = limites


def limites_catalogo():
    cfg = json.loads((DIR_APP/'fast-boot.json').read_text())
    ram = int(float(cfg.get('ram_budget_gib', 28))*GIB)
    ssd = int(float(cfg.get('ssd_budget_gib', 100))*GIB)
    reserva = float(cfg.get('ram_reserve_percent', 10))
    if ram <= 0 or ssd <= 0 or not 0 <= reserva < 100:
        raise ValueError('Límites RAM/SSD o reserva inválidos.')
    return {'ram': int(ram*(1-reserva/100)), 'ssd': ssd,
            'ram_total': ram, 'reserve_percent': reserva}


def peso_catalogo(ent):
    val = ent.get('size_bytes', ent.get('size'))
    return val if isinstance(val, int) and not isinstance(val, bool) and val > 0 else None


def modo_catalogo(ent):
    return 'origin' if ent.get('remote_only') else ent.get('selection_mode', ent.get('download_class', 'origin'))


def uso_catalogo(entradas):
    ram = ssd = desconocidos = 0
    for ent in entradas:
        modo = modo_catalogo(ent)
        if modo == 'origin':
            continue
        peso = peso_catalogo(ent)
        if peso is None:
            desconocidos += 1
        else:
            ssd += peso  # Light archives also occupy the persistent cache.
            if modo == 'light':
                ram += peso
    return {'ram': ram, 'ssd': ssd, 'unknown': desconocidos}


def cabe_catalogo(entradas, limites):
    uso = uso_catalogo(entradas)
    return not uso['unknown'] and uso['ram'] <= limites['ram'] and uso['ssd'] <= limites['ssd']


def incorpora_catalogo(ent, seleccion, limites, modo=None):
    """Keep every requested resource visible; unbounded payloads stay upstream."""
    copia = dict(ent)
    modo = modo or modo_catalogo(copia)
    if modo not in ('light', 'heavy', 'origin'):
        modo = 'origin'
    if copia.get('remote_only'):
        modo = 'origin'
    copia['selection_mode'] = modo
    if modo != 'origin':
        copia['download_class'] = modo
    resto = [e for e in seleccion.values() if e['id'] != copia['id']]
    motivo = ''
    if not cabe_catalogo(resto+[copia], limites):
        motivo = 'sin tamaño' if peso_catalogo(copia) is None else 'sin espacio'
        copia['requested_selection_mode'] = modo
        copia['selection_mode'] = 'origin'
    seleccion[copia['id']] = copia
    return motivo


def urls_defecto():
    return {lin.strip(): clase for clase in ('light', 'heavy')
            for lin in (DIR_APP/(clase+'-url.txt')).read_text().splitlines()
            if lin.strip() and not lin.lstrip().startswith('#')}


def preset_catalogo(entradas, preset, limites):
    seleccion = {}
    if preset == 'custom':
        return seleccion
    if preset == 'default':
        urls = urls_defecto()
        for ent in entradas:
            if ent.get('original_url') in urls:
                incorpora_catalogo(ent, seleccion, limites, urls[ent['original_url']])
    elif preset == 'suggested':
        # Select one local x86_64 image per family; retain upstream fallbacks.
        for familia in RECOMENDADOS:
            candidatos = [e for e in entradas if e.get('family') == familia]
            candidatos.sort(key=lambda e: (
                bool(e.get('remote_only')),
                e.get('architecture') not in ('x86_64', 'amd64', 'multiarch'),
                peso_catalogo(e) is None,
                e.get('download_class') != 'light', str(e.get('id'))))
            if candidatos:
                incorpora_catalogo(candidatos[0], seleccion, limites)
    else:
        raise ValueError('Preset desconocido.')
    return seleccion
