# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Encode PASCDE without letting observations become execution instructions."""
import re

RAM, SSD, ORIGIN, BASTION = 1, 2, 4, 8
DOWNLOAD, UPDATE, PRESERVE, ARCHIVE = 0x10, 0x20, 0x40, 0x80
PXE_CANDIDATE, RESOLVE = 0x400, 0x800
LOCATIONS = {'ram': RAM, 'ssd': SSD, 'origin': ORIGIN, 'bastion': BASTION}


def numero(val, ancho=3):
    if isinstance(val, str) and re.fullmatch('[0-9a-fA-F]{'+str(ancho)+'}', val):
        return int(val, 16)
    raise ValueError('Usar exactamente '+str(ancho)+' caracteres hexadecimales.')


def politica(val):
    return numero(val, 3)


def combina(pol, disponibilidad=0, estado=0, prioridad='0'):
    val = politica(pol) | (numero(prioridad,1)<<20)
    if any(type(x) is not int or not 0 <= x <= 15 for x in (disponibilidad, estado)):
        raise ValueError('A y S requieren valores de cuatro bits.')
    return f'{(disponibilidad << 16) | (estado << 12) | val:06X}'


def separa(val):
    num = numero(val, 6)
    return {'policy': f'{num & 0xFFF:03X}', 'availability': (num >> 16) & 15,
            'state': (num >> 12) & 15, 'priority': f'{(num >> 20) & 15:X}'}


def acciones(val):
    num = politica(val)
    return {'download': bool(num & DOWNLOAD), 'update': bool(num & UPDATE),
            'preserve': bool(num & (PRESERVE | ARCHIVE)), 'archive': bool(num & ARCHIVE),
            'locations': [nom for nom, bit in LOCATIONS.items() if num & bit],
            'crawl_level': (num >> 8) & 3, 'pxe_candidate': bool(num & PXE_CANDIDATE),
            'resolve': bool(num & RESOLVE)}


def orden_prioridad(ent,sectores=()):
    """Mandatory and user choices lead; sector hints only rank their declared scope."""
    val=numero(ent.get('priority','0'),1)
    scope=ent.get('priority_sectors') or ent.get('presets') or (['fedora','debian','alpine'] if ent.get('deploy_method')=='chroot' and ent.get('procedure_url') else [ent.get('family')])
    sector=bool(set(scope)&set(sectores))
    return (not bool(val&4),not bool(val&1),not bool(val&2 and sector),not bool(val&8 and sector))
