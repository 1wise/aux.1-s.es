# Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
# Author & Credits: https://www.alawise.es/1-s
"""Authenticate Arch's signed netboot payloads before pinning their local digest."""
import hashlib
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from .common import DIR_APP

FINGERPRINT='991F6E3F0765CF6295888586139B09DA5BF0D338'


def admite(url):return bool(re.fullmatch(r'https://archlinux\.org/static/netboot/ipxe-arch\.(?:efi|lkrn|pxe)',url))


def verifica(payload,signature,key=None):
    if not shutil.which('gpg'):raise ValueError('Arch netboot requiere gpg para verificar su firma oficial (gnupg2 en Fedora; gnupg en Debian/Alpine).')
    key=Path(key) if key else DIR_APP/'config/trust/arch-netboot.asc'
    with tempfile.TemporaryDirectory(prefix='aux-arch-signature-') as tmp:
        p=Path(tmp);ring=p/'keys.gpg';base=['gpg','--no-options','--batch','--no-autostart','--homedir',str(p)]
        ret=subprocess.run(base+['--dearmor','--output',str(ring),str(key)],capture_output=True,text=True)
        if ret.returncode:raise ValueError('No se puede leer la clave pública incluida para Arch netboot.')
        ret=subprocess.run(base+['--no-default-keyring','--keyring',str(ring),'--no-auto-key-retrieve','--status-fd','1','--verify',str(signature),str(payload)],capture_output=True,text=True)
        valid=[l.split() for l in ret.stdout.splitlines() if l.startswith('[GNUPG:] VALIDSIG ')]
        rejected=any('[GNUPG:] '+s in ret.stdout for s in ('BADSIG','ERRSIG','EXPKEYSIG','REVKEYSIG','EXPSIG','KEYREVOKED'))
        if ret.returncode or rejected or len(valid)!=1 or valid[0][-1]!=FINGERPRINT:raise ValueError('Firma de Arch netboot inválida o firmante no autorizado; no se publica el archivo.')
        return {'fingerprint':FINGERPRINT,'signing_fingerprint':valid[0][2],'signed_at':valid[0][3],'signature_sha256':hashlib.sha256(Path(signature).read_bytes()).hexdigest()}


def resuelve(ent,cache):
    url=ent['original_url']
    if not admite(url):raise ValueError('Origen Arch netboot no autorizado.')
    from .catalog import consulta
    # Bound these executable bootstrap files independently of large distribution images.
    payload=consulta(url,['archlinux.org'],cache,2097152);sig=consulta(url+'.sig',['archlinux.org'],cache,65536)
    with tempfile.TemporaryDirectory(prefix='aux-arch-payload-') as tmp:
        p=Path(tmp);(p/'payload').write_bytes(payload);(p/'signature').write_bytes(sig);proof=verifica(p/'payload',p/'signature')
    return {'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload),'signature_source':url+'.sig',
            'signature_verification':proof,'hash_origin':'computed-after-pgp-verification','checksum_source':None,'release':'netboot-'+proof['signed_at']}
