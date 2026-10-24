#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Consent-based root SSH with separate local controls and two read-only views."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import urllib.parse
import urllib.request

DIR_APP = Path(__file__).resolve().parent
DIR_RUN = Path('/run/aux-assist')
SOC_TMX = DIR_RUN / 'tmux.sock'
URL_PER = 'https://tec.1-s.es/profiles.php'
PORT_SSH = 4242
TIP_CLA = {'ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256',
           'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521'}


def ejecuta(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def texto(txt, tam=200):
    if not isinstance(txt, str) or not txt.strip() or len(txt) > tam:
        raise ValueError('Campo vacío o demasiado largo.')
    if any(ord(car) < 32 or ord(car) == 127 for car in txt):
        raise ValueError('Caracteres de control no permitidos.')
    return txt.strip()


def valida_clave(txt):
    if not isinstance(txt, str) or len(txt.encode()) > 16384:
        raise ValueError('Clave pública inválida.')
    lin = [val.strip() for val in txt.splitlines() if val.strip()]
    if len(lin) != 1:
        raise ValueError('Se requiere exactamente una clave pública OpenSSH.')
    par = lin[0].split()
    if len(par) < 2 or par[0] not in TIP_CLA:
        raise ValueError('Clave pública OpenSSH sin opciones; nunca una clave privada.')
    cla = f'{par[0]} {par[1]}\n'
    # ssh-keygen validates the entire key, not just its encoded algorithm name.
    res = subprocess.run(['ssh-keygen', '-l', '-f', '/dev/stdin', '-E', 'sha256'],
                         input=cla, text=True, capture_output=True)
    if res.returncode:
        raise ValueError('Contenido de clave pública inválido.')
    return cla


def valida_perfiles(dat):
    if not isinstance(dat, list) or len(dat) > 100:
        raise ValueError('Lista de perfiles inválida; máximo 100.')
    sal = []
    for ent in dat:
        if not isinstance(ent, dict) or set(ent) != {'nombre', 'contacto', 'clave'}:
            raise ValueError('Perfil público: solo nombre, contacto y clave.')
        sal.append({'nombre': texto(ent['nombre']), 'contacto': texto(ent['contacto']),
                    'clave': valida_clave(ent['clave'])})
    return sal


class SoloHTTPS(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise ValueError('Redirección a un protocolo distinto de HTTPS rechazada.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def descarga(url, tam=65536):
    part = urllib.parse.urlsplit(url)
    if part.scheme != 'https' or not part.hostname or part.username or part.password:
        raise ValueError('URL HTTPS sin credenciales requerida.')
    with urllib.request.build_opener(SoloHTTPS()).open(url, timeout=15) as rsp:
        dat = rsp.read(tam + 1)
    if len(dat) > tam:
        raise ValueError('Respuesta demasiado grande.')
    return dat.decode('utf-8')


def red():
    res = ejecuta(['ip', '-j', 'address', 'show', 'up'], capture_output=True, text=True)
    return [adr['local'] for ent in json.loads(res.stdout)
            for adr in ent.get('addr_info', []) if adr.get('scope') == 'global'
            and adr.get('family') in ('inet', 'inet6')]


def huella(pth):
    return ejecuta(['ssh-keygen', '-lf', str(pth), '-E', 'sha256'],
                   capture_output=True, text=True).stdout.strip()


def estado(txt):
    # Observers read only this bounded text, never keys or raw SSH logs.
    DIR_RUN.mkdir(mode=0o700, exist_ok=True)
    os.chmod(DIR_RUN, 0o700)
    (DIR_RUN / 'status.txt').write_text(txt)


def etiqueta(pth, tip):
    # Label ephemeral files for the existing Fedora SSH policy; do not disable it.
    if Path('/sys/fs/selinux/enforce').exists():
        ejecuta(['chcon', '-t', tip, str(pth)])


def ia_disponible():
    try:
        return json.loads((DIR_APP / 'ai.json').read_text()).get('enabled', True) is True
    except (OSError, ValueError, AttributeError):
        return False


def inicia_ia(prov):
    uni, tty = {'openai': ('aux-gpt.service', '4'), 'gemini': ('aux-gemini.service', '5')}[prov]
    if not ia_disponible():
        raise ValueError('Asistentes API desactivados en esta ISO.')
    pth_usb = DIR_APP / 'portable_usb.py'
    if pth_usb.is_file():
        # Only the root console may stage keys from the verified persistent medium.
        ejecuta(['/usr/bin/python3', str(pth_usb), 'api-stage', '--provider', prov])
    ejecuta(['systemctl', 'start', uni])
    ejecuta(['chvt', tty])


def selecciona(dat):
    while True:
        print('\033[2J\033[H\033[1;34mtec.* / Fedora 44 Assist 6.3.0-dev.2\033[0m')
        print('SSH cerrado. /work y cambios del live se pierden al reiniciar.\n')
        for idx, ent in enumerate(dat, 1):
            print(f"  {idx}. {ent['nombre']} | {ent['contacto']}")
        print('  P. Cargar técnicos desde TEC por HTTPS')
        print('  C. Asistencia SSH directa: URL HTTPS de clave pública')
        print('  W. Solicitar asistencia por terminal web')
        print('  T. Terminal root local (volver con exit)')
        if ia_disponible():
            print('  G. GPT Assist por API (Ctrl-Alt-F4)')
            print('  M. Gemini Assist por API (Ctrl-Alt-F5)')
            print('  I. Cerrar ambas sesiones API y liberar sus claves')
            if (DIR_APP / 'portable_usb.py').is_file():
                print('  K. Preparar o borrar claves API guardadas en la llave')
            print('  E. Revisar, aprobar, simular o deshacer planes AI (consola root)')
        print('  N. Configurar red (nmtui)')
        print('  R. Reiniciar     A. Apagar\n')
        opt = input('Opción: ').strip().lower()
        if opt in ('r', 'a'):
            ejecuta(['systemctl', 'reboot' if opt == 'r' else 'poweroff'])
        elif opt == 'p':
            url = input(f'URL de perfiles [{URL_PER}]: ').strip() or URL_PER
            dat = valida_perfiles(json.loads(descarga(url)))
        elif opt == 'n':
            subprocess.run(['nmtui'], check=False)
        elif opt == 't':
            subprocess.run(['/bin/bash', '--login'], cwd='/work', check=False)
        elif opt in ('g', 'm'):
            inicia_ia('openai' if opt == 'g' else 'gemini')
        elif opt == 'i':
            ejecuta(['systemctl', 'stop', 'aux-gpt.service', 'aux-gemini.service'])
            if (DIR_APP / 'portable_usb.py').is_file():
                ejecuta(['/usr/bin/python3', str(DIR_APP / 'portable_usb.py'), 'api-clear'])
                print('Sesiones API cerradas; las claves guardadas en la llave se conservan. K permite borrarlas.')
        elif opt == 'k' and ia_disponible() and (DIR_APP / 'portable_usb.py').is_file():
            subprocess.run(['/usr/bin/python3', str(DIR_APP / 'portable_usb.py'), 'api-keys'], check=False)
        elif opt == 'e':
            ejecuta(['systemctl', 'start', 'aux-exec.service'])
            try:
                subprocess.run(['/usr/bin/python3', str(DIR_APP / 'aux_exec.py'), 'review'], check=False)
            except KeyboardInterrupt:
                pass
        elif opt == 'w':
            try:
                subprocess.run(['/usr/bin/python3', str(DIR_APP / 'agent.py')], check=False)
            except KeyboardInterrupt:
                # The child revokes SSH before returning to the local menu.
                pass
            finally:
                subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
                limpia()
        elif opt == 'c':
            url = input('URL HTTPS de clave pública SSH: ').strip()
            cla = descarga(url, 16384)
            return {'nombre': urllib.parse.urlsplit(url).hostname, 'contacto': url,
                    'clave': valida_clave(cla)}
        elif opt.isdigit() and 1 <= int(opt) <= len(dat):
            return dat[int(opt) - 1]


def configura_ssh():
    return f'''Port {PORT_SSH}
ListenAddress 0.0.0.0
ListenAddress ::
HostKey {DIR_RUN / 'host_ed25519'}
PidFile {DIR_RUN / 'sshd.pid'}
AuthorizedKeysFile {DIR_RUN / 'authorized_keys'}
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
UsePAM yes
AllowUsers root
DisableForwarding yes
PermitUserRC no
PermitTTY yes
StrictModes yes
MaxAuthTries 3
LoginGraceTime 30
MaxStartups 2:50:5
ForceCommand /usr/bin/bash {DIR_APP / 'remote-shell.sh'}
LogLevel VERBOSE
'''


def limpia():
    if SOC_TMX.exists():
        subprocess.run(['tmux', '-S', str(SOC_TMX), 'kill-server'],
                       stderr=subprocess.DEVNULL, check=False)
    for nom in ('authorized_keys', 'host_ed25519', 'host_ed25519.pub', 'sshd.conf'):
        (DIR_RUN / nom).unlink(missing_ok=True)
    estado('ASISTENCIA CERRADA | SSH detenido. /work conservado hasta reiniciar.\n')


def sesion(ent):
    if 'aux.persist=1' in Path('/proc/cmdline').read_text().split():
        import support_case
        support_case.directa(ent)
        return
    srv = None
    try:
        print(f"\nTécnico: {ent['nombre']}\nContacto: {ent['contacto']}")
        arc = DIR_RUN / 'authorized_keys'
        arc.write_text(ent['clave'])
        arc.chmod(0o600)
        etiqueta(DIR_RUN, 'var_run_t')
        etiqueta(arc, 'ssh_home_t')
        print('Huella del técnico:', huella(arc))
        print('Acceso root: permite modificar discos y todos los datos del equipo.')
        print('Verificar contacto y huella antes de autorizar.')
        if input('Escribir AUTORIZO para abrir SSH: ').strip() != 'AUTORIZO':
            return
        ejecuta(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f',
                 str(DIR_RUN / 'host_ed25519')])
        etiqueta(DIR_RUN / 'host_ed25519', 'sshd_key_t')
        etiqueta(DIR_RUN / 'host_ed25519.pub', 'sshd_key_t')
        tmx = ['tmux', '-S', str(SOC_TMX)]
        cfg = DIR_RUN / 'tmux.conf'
        cfg.write_text('set -g status-style bg=blue,fg=white\n'
                       'set -g status-left " tec.* | ASISTENCIA "\n'
                       'set -g status-right "Cliente: Ctrl-Alt-F6 cierra SSH "\n'
                       'set -g mouse off\nset -g default-shell /bin/bash\n')
        ejecuta(tmx + ['-f', str(cfg), 'new-session', '-d', '-s', 'assist',
                      '-c', '/work', '/bin/bash --noprofile --norc'])
        sshd = DIR_RUN / 'sshd.conf'
        sshd.write_text(configura_ssh())
        etiqueta(sshd, 'etc_t')
        ejecuta([shutil.which('sshd'), '-t', '-f', str(sshd)])
        srv = True
        ejecuta(['systemctl', 'start', 'aux-assist-sshd.service'])
        time.sleep(0.5)
        if subprocess.run(['systemctl', 'is-active', '--quiet', 'aux-assist-sshd.service']).returncode:
            raise RuntimeError('SSHD no inició; revisar journalctl -u aux-assist-sshd.service.')
        lineas = ['ASISTENCIA ACTIVA | ' + ent['nombre'],
                  'Huella SSH efímera: ' + huella(DIR_RUN / 'host_ed25519.pub')]
        for adr in red():
            dst = f'[{adr}]' if ':' in adr else adr
            lineas.append(f'ssh -tt -p {PORT_SSH} -i CLAVE_PRIVADA root@{dst}')
        lineas += ['Ctrl-Alt-F7: intervención (solo lectura)',
                   'Ctrl-Alt-F8: estado (solo lectura)',
                   'Ctrl-Alt-F6: volver al control y cerrar la sesión']
        txt = '\n'.join(lineas) + '\n'
        estado(txt)
        print('\n' + txt)
        print('El acceso requiere ruta directa/intranet/VPN ya configurada.')
        input('Enter CIERRA SSH y termina las terminales del técnico: ')
    finally:
        if srv is not None:
            subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
        limpia()


def observa(num):
    # These processes never start a shell and never read a local command line.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    if num == 7:
        while True:
            if SOC_TMX.exists():
                subprocess.run(['tmux', '-S', str(SOC_TMX), 'attach-session', '-r',
                                '-t', 'assist'], check=False)
            else:
                print('\033[2J\033[Htec.* / Intervención · solo lectura\n'
                      'Esperando asistencia. Ctrl-Alt-F6: control local.', flush=True)
            time.sleep(1)
    elif num == 8:
        while True:
            arc = DIR_RUN / 'status.txt'
            txt = arc.read_text() if arc.exists() else 'SSH cerrado; pendiente de autorización.\n'
            print('\033[2J\033[Htec.* / Estado · solo lectura\n\n' + txt,
                  flush=True)
            subprocess.run(['free', '-h'], check=False)
            subprocess.run(['df', '-h', '/', '/work'], check=False)
            time.sleep(2)
    else:
        raise ValueError('Solo se admiten los visores 7 y 8.')


def main():
    os.umask(0o077)
    if os.geteuid() != 0:
        raise RuntimeError('Ejecutar dentro de la ISO como root.')
    for nom in ('sshd', 'tmux', 'ip', 'ssh-keygen', 'nmtui'):
        if not shutil.which(nom):
            raise RuntimeError('Falta herramienta: ' + nom)
    subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
    limpia()
    # A manually selected GRUB/iPXE entry can open the API terminal after the Live boots.
    for arg in Path('/proc/cmdline').read_text().split():
        if arg in ('aux.ai=openai', 'aux.ai=gemini') and ia_disponible():
            try:
                inicia_ia(arg.split('=', 1)[1])
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                print('Asistente API no iniciado; menú local disponible:', exc)
            break
    def termina(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, termina)
    import support_case
    cas = support_case.carga()
    if cas:
        print('Restoring authorized support case:', cas['id'])
        if cas['mode'] == 'web':
            subprocess.run(['/usr/bin/python3', str(DIR_APP / 'agent.py'), '--resume'], check=False)
        else:
            support_case.reanuda_directa(cas)
    while True:
        try:
            dat = valida_perfiles(json.loads((DIR_APP / 'profiles.json').read_text()))
            sesion(selecciona(dat))
        except KeyboardInterrupt:
            limpia()
            return
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            limpia()
            print('\nAsistencia no iniciada:', exc)
            input('Enter para volver al menú: ')


if __name__ == '__main__':
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--observe', type=int, choices=(7, 8))
    cfg = par.parse_args()
    if cfg.observe:
        observa(cfg.observe)
    else:
        main()
