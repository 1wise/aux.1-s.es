#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
# iPXE command semantics: https://ipxe.org
"""Shared data, validation and file utilities; no command is dispatched here."""

import argparse
import contextlib
import base64
import concurrent.futures
import configparser
import datetime as dt
import fcntl
import hashlib
import html
import io
import json
import os
import pwd
import grp as grp_sys
import stat
from pathlib import Path
import copy
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.parse import urlsplit, unquote, quote, urlunsplit
import xml.etree.ElementTree as ET
import zipfile

DEFAULT_URLS = globals().get('DEFAULT_URLS', '')
TEMPLATES = globals().get('TEMPLATES', {})
BINARY_ASSETS = globals().get('BINARY_ASSETS', {})
VERSION = '6.3.0-dev.2'
CREDITS = 'https://www.alawise.es/1-s'
mtx_log = threading.Lock()
uid_pub, gid_pub = os.geteuid(), os.getegid()


SOURCE_FILES = {}
EXT_PAYLOAD = ('.iso', '.zip', '.tar.gz', '.efi', '.kpxe', '.pxe', '.lkrn', '.img', '.img.xz', '.qcow2', '.bin')


def es_payload(nom):
    return bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', nom)) and nom.lower().endswith(EXT_PAYLOAD)


def lee_fuentes(cfg):
    """Optional download metadata labels discovered files; it never marks them published."""
    arc = cfg.cache / 'downloads.json'
    if not arc.is_file():
        return {}
    datos = json.loads(arc.read_text())
    return {rec['filename']: rec['url'] for rec in datos.get('resources', [])
            if isinstance(rec, dict) and rec.get('filename') and rec.get('url')}


def lee_cache(cfg):
    # Explicit lists select names locally; a missing payload fails in deploy validation.
    # Without a list, discovery still works with only the cache and no URL files.
    if getattr(cfg, 'url_file', None):
        return obt_catalog(Path(cfg.url_file).read_text(), cfg.only)
    fuentes = lee_fuentes(cfg)
    rec_all = []
    for arc in sorted(cfg.cache.iterdir()) if cfg.cache.is_dir() else []:
        if not es_payload(arc.name) or not arc.is_file():
            continue
        rec = obt_meta(fuentes.get(arc.name, cfg.pxe_url + '/' + quote(arc.name, safe='')))
        if rec['filename'] != arc.name:
            raise ValueError('Cached filename differs from its download record: ' + arc.name)
        if not cfg.only or cfg.only.lower() in (rec['family'] + ' ' + arc.name).lower():
            rec_all.append(rec)
    if not rec_all:
        raise ValueError('No cached payloads selected; run download.sh first')
    return rec_all


def configura(txt_urls, tpl, bin_assets, arc_src=None):
    """Keep generation templates and optional source files separate from execution."""
    global DEFAULT_URLS
    DEFAULT_URLS = txt_urls
    for des, src in [(TEMPLATES, tpl), (BINARY_ASSETS, bin_assets), (SOURCE_FILES, arc_src or {})]:
        des.clear()
        des.update(src)


def obt_args(cmd, pth_app):
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--config')
    cfg_pre, _ = pre.parse_known_args()
    arc_cfg = Path(cfg_pre.config).expanduser().resolve() if cfg_pre.config else pth_app / 'fast-boot.json'
    val_cfg = {}
    if arc_cfg.is_file():
        val_cfg = json.loads(arc_cfg.read_text())
        if not isinstance(val_cfg, dict):
            pre.error('Configuration must be a JSON object')
        val_cfg.pop('_meta', None)
    elif cfg_pre.config:
        pre.error(f'Configuration not found: {arc_cfg}')
    allowed = {'output', 'cache', 'base_url', 'pxe_url', 'download_url', 'live_url', 'ram_dir', 'url_file', 'checksums', 'jobs',
               'ftp_host', 'ftp_user', 'ftp_port', 'ftp_root', 'ftp_tls', 'user', 'group',
               'light_url_file', 'heavy_url_file', 'tec', 'bastion', 'boot', 'hosts', 'tls', 'php_profiles', 'platform',
               'targets', 'target', 'generate', 'cli', 'ai', 'ram_budget_gib', 'ram_reserve_percent'}
    if set(val_cfg) - allowed:
        pre.error('Unknown configuration keys: ' + ', '.join(sorted(set(val_cfg) - allowed)))
    if val_cfg.get('platform', 'fedora') not in ('fedora', 'debian'):
        pre.error('platform must be fedora or debian')
    for nom in ['tec', 'bastion', 'boot', 'hosts', 'tls', 'php_profiles', 'targets', 'generate', 'cli', 'ai']:
        if nom in val_cfg and not isinstance(val_cfg[nom], dict):
            pre.error('Configuration ' + nom + ' must be an object')
    if 'ai' in val_cfg and type(val_cfg['ai'].get('enabled', True)) is not bool:
        pre.error('ai.enabled must be true or false')
    ia = val_cfg.get('ai', {})
    if set(ia) - {'enabled', 'openai', 'gemini', 'timeout_seconds', 'max_output_tokens'}:
        pre.error('ai accepts public settings only; API keys must never enter fast-boot.json')
    for nom in ('openai', 'gemini'):
        ent = ia.get(nom, {})
        if not isinstance(ent, dict) or set(ent) - {'model'}:
            pre.error('ai.' + nom + ' accepts model only; no credentials')
        mod = ent.get('model')
        if mod is not None and (not isinstance(mod, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', mod)):
            pre.error('Invalid AI model identifier: ' + nom)
    for nom, minimo, maximo in [('timeout_seconds', 10, 120), ('max_output_tokens', 128, 4096)]:
        if nom in ia and (type(ia[nom]) is not int or not minimo <= ia[nom] <= maximo):
            pre.error('ai.' + nom + ' outside supported integer bounds')
    for nom, hosts in val_cfg.get('hosts', {}).items():
        if not isinstance(hosts, list) or not hosts or any(not isinstance(h, str) or not re.fullmatch(r'[A-Za-z0-9.-]+', h) for h in hosts):
            pre.error('Invalid host list: ' + nom)
    for nom, hosts in val_cfg.get('bastion', {}).items():
        if nom not in ('web_hosts', 'cli_hosts', 'tec_hosts') or not isinstance(hosts, list) or any(not isinstance(h, str) or not re.fullmatch(r'[A-Za-z0-9.-]+', h) for h in hosts):
            pre.error('Invalid Bastion host list: ' + nom)
    espera = val_cfg.get('boot', {}).get('assist_timeout_seconds', 60)
    if not isinstance(espera, int) or isinstance(espera, bool) or not 0 <= espera <= 3600:
        pre.error('boot.assist_timeout_seconds must be an integer from 0 to 3600')
    for nom in ['output', 'cache', 'ram_dir', 'url_file', 'light_url_file', 'heavy_url_file', 'checksums']:
        if val_cfg.get(nom):
            if not isinstance(val_cfg[nom], str):
                pre.error(f'Configuration {nom} must be a path string')
            pth = Path(val_cfg[nom]).expanduser()
            val_cfg[nom] = str(pth if pth.is_absolute() else arc_cfg.parent / pth)
    if cmd != 'download':
        # Existing url_file settings belong to download, not implicit deploy filtering.
        val_cfg.pop('url_file', None)
    des = {'download': 'Download url.txt into the persistent cache.',
           'deploy': 'Deploy cached files to RAM, disk, or merge the public tree and cache over FTP.',
           'generate': 'Crawl public units and generate AUX/PXE indexes, menus and sitemaps.'}
    arg = argparse.ArgumentParser(prog=cmd + '.sh', description=des[cmd])
    arg.add_argument('--config', help='Shared JSON settings; fast-boot.json beside this script is loaded automatically')
    arg.add_argument('--output', default='/var/www/aux.1-s.es/html', help='Public unit root, independent from the cache')
    arg.add_argument('--cache', help='Persistent cache outside the webroot; defaults to a sibling isos directory')
    arg.add_argument('--base-url', default='https://aux.1-s.es', help='Canonical AUX visual portal URL')
    arg.add_argument('--pxe-url', default='http://pxe.1-s.es', help='Excalibur URL for PXE and deployed image files')
    arg.add_argument('--download-url', default='https://b.1-s.es', help='Bastion base URL for complete downloads; preserve public relative paths')
    arg.add_argument('--ram-dir', default='/dev/shm/aux-fast-boot', help='Directory on an already mounted tmpfs')
    arg.add_argument('--checksums', help='Optional trusted SHA256SUMS file')
    arg.add_argument('--user', help='Managed file user (name or uid); default: executing user')
    arg.add_argument('--group', help='Managed file group (name or gid); default: selected user primary group')
    arg.add_argument('--target', help='Public URL profile from targets; does not run another command')
    arg.add_argument('--only', help='Select resources by family or filename substring')
    arg.add_argument('--dry-run', action='store_true', help='Inspect this command without writes or network calls')
    if cmd in ('download', 'deploy'):
        sel = arg.add_mutually_exclusive_group()
        sel.add_argument('--url-file', default=str(pth_app / 'url.txt') if cmd == 'download' else None,
                         help='Select one HTTP(S) payload URL per line; deploy reads cached files only')
        sel.add_argument('--list', dest='sel_lis', choices=['light', 'heavy'],
                         help='Select light-url.txt or heavy-url.txt; no target is chosen automatically')
        arg.add_argument('--light-url-file', default=str(pth_app / 'light-url.txt'), help='Path used by --list light')
        arg.add_argument('--heavy-url-file', default=str(pth_app / 'heavy-url.txt'), help='Path used by --list heavy')
    if cmd == 'download':
        arg.add_argument('--jobs', type=int, default=4, help='Parallel downloads, from 1 to 16')
        arg.add_argument('--refresh', action='store_true', help='Download again, retaining the valid cache on failure')
    elif cmd == 'deploy':
        arg.add_argument('dest', choices=['ram', 'disk', 'ftp'], help='Deployment target; FTP merges html/ and cached payloads at the remote root')
        arg.add_argument('--mode', choices=['mount', 'extract'], help='Disk deployment defaults to extract; RAM mounts ISO contents')
        arg.add_argument('--mount-context', help='Optional SELinux context for read-only ISO mounts, e.g. system_u:object_r:httpd_sys_content_t:s0')
        arg.add_argument('--ftp-host', default=os.environ.get('AUX_FTP_HOST'), help='FTP hostname, without scheme or credentials')
        arg.add_argument('--ftp-user', default=os.environ.get('AUX_FTP_USER'), help='FTP account; password comes from a hidden prompt or AUX_FTP_PASSWORD')
        arg.add_argument('--ftp-port', type=int, default=21)
        arg.add_argument('--ftp-root', default='/', help='Existing FTP directory mapped to the Bastion website root')
        arg.add_argument('--ftp-tls', action=argparse.BooleanOptionalAction, default=True, help='Explicit FTPS with certificate verification (default); --no-ftp-tls selects plain FTP')
    else:
        arg.add_argument('--live-url', help='Numeric IPv4 HTTP URL for Debian-style live-boot fetch')
        arg.add_argument('--tec', choices=['auto', 'on', 'off'], help='Show optional TEC navigation; auto checks tec.web_dir')
    grp = arg.add_mutually_exclusive_group()
    grp.add_argument('-v', '--verbose', dest='quiet', action='store_false', help='Show per-file progress (default)')
    grp.add_argument('-q', '--quiet', dest='quiet', action='store_true', help='Show only errors and the summary')
    arg.set_defaults(**{'quiet': False, 'jobs': 4, 'live_url': None, **val_cfg})
    arg.add_argument('--version', action='version', version=VERSION)
    cfg = arg.parse_args()
    if getattr(cfg, 'tec', None) is None:
        cfg.tec = {}
    modo_tec_cli = cfg.tec if cmd == 'generate' and isinstance(cfg.tec, str) else None
    if modo_tec_cli:
        cfg.tec = val_cfg.get('tec', {})
    if cfg.target:
        perfil = val_cfg.get('targets', {}).get(cfg.target)
        if not isinstance(perfil, dict):
            arg.error('Unknown --target: ' + cfg.target)
        for nom in ['base_url', 'pxe_url', 'download_url']:
            flag = '--' + nom.replace('_', '-')
            if nom in perfil and not any(val == flag or val.startswith(flag + '=') for val in sys.argv):
                setattr(cfg, nom, perfil[nom])
        if perfil.get('tec_url'):
            cfg.tec = {**getattr(cfg, 'tec', {}), 'public_url': perfil['tec_url']}
    if cmd == 'generate':
        # Configuration and feature selection stay distinct from TEC application settings.
        modo_tec = modo_tec_cli or val_cfg.get('generate', {}).get('tec', 'auto')
        if modo_tec not in ('auto', 'on', 'off', True, False):
            arg.error('generate.tec must be auto, on or off')
        pth_tec = Path(getattr(cfg, 'tec', {}).get('web_dir', str(pth_app / 'tec/web')))
        listo_tec = (pth_tec / 'index.php').is_file() and (pth_tec / 'lib.php').is_file()
        if modo_tec in ('on', True) and not listo_tec:
            arg.error('TEC requested but index.php/lib.php missing in ' + str(pth_tec))
        cfg.tec_enabled = modo_tec not in ('off', False) and listo_tec
    if cmd in ('download', 'deploy'):
        if cfg.sel_lis:
            cfg.url_file = getattr(cfg, cfg.sel_lis + '_url_file')
        if cfg.url_file:
            cfg.url_file = Path(cfg.url_file).expanduser().resolve()
    cfg.stage = 'deploy-' + cfg.dest if cmd == 'deploy' else cmd
    if cmd == 'deploy':
        if cfg.mount_context and (cfg.dest == 'ftp' or cfg.dest == 'disk' and cfg.mode != 'mount'):
            arg.error('--mount-context requires RAM or disk --mode mount')
        if cfg.mount_context and not re.fullmatch(r'[A-Za-z0-9_]+:[A-Za-z0-9_]+:[A-Za-z0-9_]+:s[0-9]+', cfg.mount_context):
            arg.error('--mount-context requires a simple SELinux user:role:type:sensitivity context')
        if cfg.dest != 'disk' and cfg.mode:
            arg.error('--mode applies to disk only')
        if cfg.dest == 'ftp':
            if cfg.url_file:
                arg.error('--list/--url-file do not apply to FTP: the complete public tree is replicated')
            if cfg.only:
                arg.error('--only does not apply to FTP: the complete public tree is replicated')
            if not isinstance(cfg.ftp_port, int) or not 1 <= cfg.ftp_port <= 65535:
                arg.error('--ftp-port must be between 1 and 65535')
            if not isinstance(cfg.ftp_tls, bool):
                arg.error('ftp_tls must be true or false')
            if not isinstance(cfg.ftp_root, str) or not cfg.ftp_root.startswith('/') or any(ord(c) < 32 or ord(c) == 127 for c in cfg.ftp_root) or '..' in cfg.ftp_root.split('/'):
                arg.error('--ftp-root must be an absolute FTP directory without parent traversal or control characters')
            if cfg.ftp_host and (not isinstance(cfg.ftp_host, str) or any(c.isspace() for c in cfg.ftp_host) or any(c in cfg.ftp_host for c in '/:@')):
                arg.error('--ftp-host must be a hostname without scheme, port or credentials')
            if cfg.ftp_user and (not isinstance(cfg.ftp_user, str) or any(ord(c) < 32 or ord(c) == 127 for c in cfg.ftp_user)):
                arg.error('--ftp-user must not contain control characters')
        cfg.mode = 'ram' if cfg.dest == 'ram' else cfg.mode or 'extract'
    if not isinstance(cfg.jobs, int) or not 1 <= cfg.jobs <= 16:
        arg.error('--jobs must be an integer between 1 and 16')
    cfg.output = Path(cfg.output).expanduser().resolve()
    cfg.cache = Path(cfg.cache).expanduser().resolve() if cfg.cache else cfg.output.parent / 'isos'
    cfg.ram_dir = Path(cfg.ram_dir).expanduser().resolve()
    if cfg.output == Path('/') or cfg.cache == Path('/') or cfg.cache.is_relative_to(cfg.output):
        arg.error('The webroot cannot be /, and the cache must be outside the webroot')
    for nom in ['base_url', 'pxe_url', 'download_url', 'live_url']:
        val = getattr(cfg, nom)
        if val:
            url = urlsplit(val)
            if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password or url.query or url.fragment or any(c.isspace() for c in val):
                arg.error(f'--{nom.replace("_", "-")} must be a plain HTTP(S) URL without credentials, query or fragment')
            setattr(cfg, nom, val.rstrip('/'))
    if cfg.live_url:
        url = urlsplit(cfg.live_url)
        if url.scheme != 'http' or not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', url.hostname):
            arg.error('--live-url must use http:// and a numeric IPv4 address')
    global uid_pub, gid_pub
    try:
        usr = pwd.getpwuid(int(cfg.user)) if str(cfg.user).isdigit() else pwd.getpwnam(cfg.user) if cfg.user is not None else pwd.getpwuid(os.geteuid())
        uid_pub = usr.pw_uid
        if cfg.group is not None:
            gid_pub = int(cfg.group) if str(cfg.group).isdigit() else grp_sys.getgrnam(cfg.group).gr_gid
        else:
            gid_pub = usr.pw_gid
        if uid_pub < 0 or gid_pub < 0:
            raise ValueError('Owner/group ids must be nonnegative')
        if os.geteuid() != 0 and (uid_pub != os.geteuid() or gid_pub not in {os.getegid(), *os.getgroups()}):
            raise ValueError('Requested owner/group requires root or membership in that group')
    except (KeyError, TypeError, ValueError) as exc:
        arg.error('Invalid --user/--group: ' + str(exc))
    cfg.uid_pub, cfg.gid_pub = uid_pub, gid_pub
    presupuesto = getattr(cfg, 'ram_budget_gib', 22)
    reserva = getattr(cfg, 'ram_reserve_percent', 10)
    if isinstance(presupuesto, bool) or not isinstance(presupuesto, (int, float)) or not 0 < presupuesto <= 1024:
        arg.error('ram_budget_gib must be a positive number up to 1024')
    if isinstance(reserva, bool) or not isinstance(reserva, (int, float)) or not 0 <= reserva < 100:
        arg.error('ram_reserve_percent must be a number from 0 to less than 100')
    global cfg_activa
    cfg_activa = cfg
    return cfg


def obt_sumas(cfg):
    sumas = {}
    if cfg.checksums:
        for lin in Path(cfg.checksums).read_text().splitlines():
            par = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?(.+)', lin)
            if par:
                sumas[par.group(2)] = par.group(1).lower()
            elif lin.strip() and not lin.lstrip().startswith('#'):
                raise ValueError('Malformed trusted SHA256SUMS record')
        if not sumas:
            raise ValueError('The trusted checksum list is empty')
    return sumas


@contextlib.contextmanager
def bloq_cache(cfg):
    """Serialize filesystem changes without coupling the three command implementations."""
    with (cfg.cache / '.fast-boot.lock').open('a') as arc:
        try:
            fcntl.flock(arc, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another command is using this cache')
        try:
            yield
        finally:
            fcntl.flock(arc, fcntl.LOCK_UN)


def muestra_plan(cfg, rec_all):
    print(f'{cfg.stage} {VERSION} | resources={len(rec_all)}')
    print(f'Cache: {cfg.cache}\nPublic units: {cfg.output}\nRAM: {cfg.ram_dir}\nBoot URL: {cfg.pxe_url}')
    if getattr(cfg, 'url_file', None):
        print(f'Selection list: {cfg.url_file}')
    for rec in rec_all:
        print(f'{rec["arch"]:7} {rec.get("path", rec["filename"])}')


def inicia_informe(cfg):
    """Keep operational diagnostics outside the public tree; never record credentials."""
    cfg._log = []
    cfg._run_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + str(os.getpid())
    cfg._log_path = cfg.cache / 'logs' / (cfg.stage + '-' + cfg._run_id + '.log')
    msg_descarga(cfg, None, 'IDENTITY', f'user={pwd.getpwuid(cfg.uid_pub).pw_name} group={cfg.gid_pub}')


def describe_error(exc):
    if isinstance(exc, subprocess.CalledProcessError):
        err = exc.stderr or exc.stdout or ''
        if isinstance(err, bytes):
            err = err.decode(errors='replace')
        return str(exc) + (': ' + err.strip() if err else '')
    return str(exc)


def sugerencia_error(txt):
    if 'Read-only' in txt:
        return 'Keep generated files outside mounted ISO contents; inspect findmnt -T PATH.'
    if 'space' in txt.lower() or 'budget' in txt.lower():
        return 'Check df -h and free -h; deploy this resource to disk or reduce the RAM selection.'
    if 'ermission' in txt:
        return 'Check namei -l, selected --user/--group and SELinux AVC records.'
    if 'checksum' in txt.lower():
        return 'Compare against an official trusted SHA-256; retain the previous verified file.'
    return 'Inspect the full stage log and retry this resource with --only FILENAME.'


def ejecuta_main(fn):
    try:
        return fn()
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        cfg = globals().get('cfg_activa')
        if cfg and hasattr(cfg, '_log'):
            return fin_tarea(cfg, [{'filename': cfg.stage, 'status': 'failed', 'size': 0,
                'error': describe_error(exc)}], time.monotonic())
        print('ERROR: ' + describe_error(exc), file=sys.stderr)
        return 1


def fin_tarea(cfg, rec_all, tms_ini):
    fails = [rec for rec in rec_all if rec.get('error') or rec.get('tree_error') or rec['status'] == 'failed']
    n_byt = sum(rec['size'] or 0 for rec in rec_all)
    print(f'{cfg.stage}: {len(rec_all) - len(fails)} OK | {len(fails)} failed | {n_byt / 1024**2:.1f} MiB | {time.monotonic() - tms_ini:.1f}s')
    for rec in fails:
        err = rec.get('error') or rec.get('tree_error') or rec['status']
        pth = rec.get('error_path') or str((cfg.cache if cfg.stage == 'download' else cfg.output) / rec.get('path', rec['filename']))
        detalle = f"FAIL: {rec['filename']}\n  stage: {rec.get('error_stage', cfg.stage)}\n  path: {pth}\n  source: {rec.get('url', '')}\n  error: {err}\n  hint: {sugerencia_error(err)}"
        print(detalle, file=sys.stderr)
        getattr(cfg, '_log', []).append(detalle)
    if hasattr(cfg, '_log_path'):
        cfg._log_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        cfg._log_path.parent.chmod(0o700)
        cfg._log_path.write_text('\n'.join(cfg._log) + '\n')
        cfg._log_path.chmod(0o600)
        print('Log: ' + str(cfg._log_path))
    return 1 if fails else 0


def obt_estado(cfg, tipo, rec):
    """Scope ownership to a webroot so one cache can feed several mirrors."""
    nom_raiz = hashlib.sha256(str(cfg.output).encode()).hexdigest()[:16]
    return cfg.cache / tipo / nom_raiz / (rec['id'] + '.json')


def lee_estado(cfg, tipo, rec):
    arc = obt_estado(cfg, tipo, rec)
    if not arc.is_file():
        arc = cfg.cache / tipo / (rec['id'] + '.json')
    if not arc.is_file():
        return {}
    dat = json.loads(arc.read_text())
    campo, nom = ('path', 'filename') if tipo == 'file-state' else ('tree', 'tree')
    return dat if dat.get(campo) == str(cfg.output / rec[nom]) else {}



def obt_meta(url):
    part = urlsplit(url)
    if part.scheme not in ('http', 'https') or not part.hostname or part.username or part.password or any(c.isspace() for c in url):
        raise ValueError(f'Invalid payload URL: {url}')
    pth = part.path.rstrip('/')
    if pth.endswith('/download'):
        pth = pth[:-9]
    nom_arc = unquote(pth.rsplit('/', 1)[-1])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', nom_arc):
        raise ValueError(f'Unsafe or missing filename in URL: {url}')
    low = nom_arc.lower()
    # Generic netboot archive names carry their distribution and architecture in the URL.
    ctx = low + ' ' + part.path.lower() if low in ('netboot.tar.gz', 'linux', 'initrd.gz') else low
    fam = next((nom for nom, pat in [
        ('alpine', 'alpine'), ('centos', 'centos-stream'), ('systemrescue', 'systemrescue'), ('rescatux', 'rescatux'), ('redo', 'redorescue'),
        ('debian', 'debian'), ('fedora', 'fedora'), ('ubuntu', 'ubuntu'),
        ('arch', 'archlinux'), ('arch', 'ipxe-arch'), ('gentoo', 'livegui'),
        ('gentoo', 'install-amd64-minimal'), ('kali', 'kali'), ('proxmox', 'proxmox'),
        ('clonezilla', 'clonezilla'), ('gparted', 'gparted'), ('memtest', 'mt86plus'), ('memtest', 'memtest'),
        ('netboot', 'netboot.xyz'), ('bootrepair', 'boot-repair'), ('dban', 'dban'),
        ('supergrub', 'supergrub')
    ] if pat in ctx), 'other')
    if 'aarch64' in ctx or 'arm64' in ctx:
        arq = 'arm64'
    elif re.search(r'(?:i[356]86|[._/-]x86(?=[./-]|$)|_32|[._-]32[._-]|memtest32)', ctx):
        arq = 'i386'
    else:
        arq = 'x86_64'
    cat = 'distribution' if fam in ('alpine', 'centos', 'debian', 'fedora', 'ubuntu', 'arch', 'gentoo', 'kali', 'proxmox') else 'tools'
    # Recognize our source names for browsing only; boot still requires media inspection.
    aux_rescue = bool(re.fullmatch(r'aux-rescue(?:-[A-Za-z0-9._+-]+)?\.iso', low))
    aux_assist = bool(re.fullmatch(r'aux-assist(?:-[A-Za-z0-9._+-]+)?\.iso', low))
    asistencia = aux_rescue or aux_assist or bool(re.match(r'(?:tec|tech)-fedora\d+-(?:assist|rescue)-', low))
    if asistencia:
        cat = 'assistance'
        fam = 'fedora'
    fmt = next((ext.upper() for ext in ['tar.gz', 'iso.zip', 'grub.iso.zip', 'img.xz', 'iso', 'efi', 'kpxe', 'pxe', 'lkrn', 'qcow2'] if low.endswith('.' + ext)), 'FILE')
    cli_boot = low.endswith(('.efi', '.kpxe', '.pxe', '.lkrn'))
    kind = ('netboot' if cli_boot or 'netboot' in low else
            'live' if any(pat in low for pat in ('live', 'desktop', 'archlinux')) else
            'install' if cat == 'distribution' else 'tool')
    if asistencia:
        kind = 'tool'
    rel = re.search(r'(?<!\d)(\d{4}\.\d{2}\.\d{2}|\d{4}\.\d+|\d+\.\d+(?:\.\d+)?(?:-\d+)?|\d{8}T\d+Z)(?!\d)', nom_arc)
    release = rel.group(1) if rel else 'Rolling'
    if fam == 'fedora':
        rel_fed = re.search(r'(?:Live-|netinst-(?:x86_64-|aarch64-)?)(\d+)-', nom_arc)
        release = 'Rawhide' if 'rawhide' in low else (rel_fed.group(1) if rel_fed else release)
    if asistencia:
        rel_tec = re.search(r'\d+\.\d+\.\d+(?:-dev\.\d+)?', nom_arc)
        if rel_tec:
            release = rel_tec.group(0)
    if 'testing' in low:
        release = 'Testing'
    if 'beta' in low:
        release += ' beta'
    base_nom = {'alpine': 'Alpine Linux', 'centos': 'CentOS Stream', 'systemrescue': 'SystemRescue', 'rescatux': 'Rescatux', 'redo': 'Redo Rescue', 'debian': 'Debian', 'fedora': 'Fedora', 'ubuntu': 'Ubuntu', 'arch': 'Arch Linux',
                'gentoo': 'Gentoo', 'kali': 'Kali Linux', 'proxmox': 'Proxmox VE',
                'clonezilla': 'Clonezilla Live', 'gparted': 'GParted Live', 'memtest': 'Memtest86+',
                'netboot': 'netboot.xyz', 'bootrepair': 'Boot Repair', 'dban': 'DBAN',
                'supergrub': 'Super GRUB2 Disk', 'other': 'Boot resource'}[fam]
    if fam == 'debian' and 'bookworm' in ctx:
        release = '12 Bookworm / oldstable'
    if fam == 'fedora' and 'cloud' in low:
        rel_cloud = re.search(r'Generic-(\d+)-', nom_arc)
        release = rel_cloud.group(1) if rel_cloud else release
    var = ''
    for pat, tit in [('gnome', 'GNOME Live'), ('xfce', 'XFCE Live'), ('purple', 'Purple Installer'),
                     ('workstation', 'Workstation Live'), ('live-server', 'Server'), ('desktop', 'Desktop'),
                     ('server-netinst', 'Server Netinstall'), ('netinst', 'Netinstall'), ('livegui', 'LiveGUI'),
                     ('minimal', 'Minimal Install'), ('installer', 'Installer')]:
        if pat in low:
            var = tit
            break
    if cli_boot:
        var = 'UEFI' if low.endswith('.efi') else ('BIOS kernel' if low.endswith('.lkrn') else 'Legacy BIOS')
    if fam == 'alpine':
        var = next((tit for pat, tit in [('netboot', 'Netboot'), ('standard', 'Standard'), ('extended', 'Extended')] if ('alpine-' + pat + '-') in low), 'Media')
    if fam == 'ubuntu' and fmt == 'TAR.GZ':
        var = 'Netboot archive'
    if fam == 'memtest' and '.grub.' in low:
        var = 'GRUB image'
    description = {
        'alpine': 'Alpine Linux: original Netboot, Standard and Extended media for compatible hardware.',
        'centos': 'CentOS Stream boot installer; media inspection and boot validation required.',
        'systemrescue': 'SystemRescue recovery media; boot recipe validation pending.',
        'rescatux': 'Rescatux recovery media; historical release, boot validation pending.',
        'redo': 'Redo Rescue backup and recovery media; boot validation pending.',
        'debian': 'Debian installation or live media from the supplied source manifest.',
        'fedora': 'Fedora workstation or server media. The source version is pinned in the URL list.',
        'ubuntu': 'Ubuntu desktop, server or network boot resources from the supplied source list.',
        'arch': 'Arch Linux rolling installation media or a native iPXE boot client.',
        'gentoo': 'Gentoo live or minimal media. Downloadable; no unverified automatic PXE recipe is emitted.',
        'kali': 'Kali installation media for authorized security work and defensive environments.',
        'proxmox': 'Proxmox virtualization installer. Downloadable; its ISO is not advertised as a complete HTTP PXE installer.',
        'clonezilla': 'Live media for disk imaging and backup. Run recovery actions deliberately on the target system.',
        'gparted': 'Partition management live media. Partition changes require a separate decision on the target system.',
        'memtest': 'Memory test media. PXE entries require actual native EFI or BIN payloads after extraction.',
        'netboot': 'A firmware-specific network boot client. Choose the binary that matches the target firmware.',
        'bootrepair': 'Boot recovery media. Local payload paths are discovered after preparation.',
        'dban': 'Legacy disk erasure media. Download only; this engine never creates an automatic disk wipe entry.',
        'supergrub': 'GRUB boot recovery image. Download only unless a recipe is explicitly supported.',
        'other': 'A payload provided in the source URL manifest.'
    }[fam]
    if fam == 'debian' and 'genericcloud' in low:
        rel_cloud = re.search(r'debian-(\d+)-', low)
        release = rel_cloud.group(1) if rel_cloud else release
    if fmt == 'QCOW2':
        var = 'Cloud / QCOW2'
        description = 'Preinstalled virtual disk for a compatible hypervisor and cloud-init; not an iPXE installer.'
    if fam == 'debian' and 'bookworm' in ctx:
        var = '12 Bookworm network installer'
    stem = re.sub(r'\.(?:grub\.iso\.zip|iso\.zip|tar\.gz|img\.xz|iso|zip)$', '', nom_arc, flags=re.I)
    return {'id': 'r_' + hashlib.sha256(nom_arc.encode()).hexdigest()[:12],
            'name': ('AUX Rescue / Remote assistance' if aux_rescue else 'AUX Assist / Web assistance' if aux_assist else 'Fedora / Remote assistance') if asistencia else f'{base_nom} {var}'.strip(),
            'family': fam, 'category': cat, 'kind': kind, 'arch': arq, 'release': release, 'format': fmt,
            'filename': nom_arc, 'tree': stem, 'url': url, 'description': description,
            'status': 'source', 'size': None, 'sha256': None, 'published': False,
            'contents_ready': False, 'pxe_ready': False, 'assistance': asistencia}



def obt_catalog(txt, sel=None):
    rec_all, url_vistos, nom_vistos = [], set(), {}
    for lin in txt.splitlines():
        url = lin.strip()
        if not url or url.startswith('#') or url in url_vistos:
            continue
        rec = obt_meta(url)
        if rec['filename'] in nom_vistos:
            raise ValueError(f'Filename collision: {rec["filename"]}; keep one source URL per filename')
        url_vistos.add(url)
        nom_vistos[rec['filename']] = url
        if not sel or sel.lower() in (rec['family'] + ' ' + rec['filename']).lower():
            rec_all.append(rec)
    if not rec_all:
        raise ValueError('The selected URL catalog is empty')
    return rec_all



def arc_valido(pth, nom_arc):
    if not pth.is_file() or pth.stat().st_size == 0:
        return False
    with pth.open('rb') as arc:
        cab = arc.read(512)
        low = cab.lstrip().lower()
        if low.startswith((b'<!doctype html', b'<html', b'<?xml', b'{"error')):
            return False
        if nom_arc.endswith('.iso'):
            arc.seek(32769)
            return arc.read(5) in (b'CD001', b'BEA01', b'NSR02', b'NSR03')
    if nom_arc.endswith('.zip'):
        return zipfile.is_zipfile(pth)
    if nom_arc.endswith('.tar.gz'):
        return tarfile.is_tarfile(pth)
    if nom_arc.endswith('.efi'):
        return cab.startswith(b'MZ')
    if nom_arc.endswith('.img.xz'):
        return cab.startswith(b'\xfd7zXZ\x00')
    return True


def arc_presente(pth):
    return pth.is_file() and pth.stat().st_size > 0



def obt_sha(pth):
    dig = hashlib.sha256()
    with pth.open('rb') as arc:
        for tro in iter(lambda: arc.read(4 * 1024 * 1024), b''):
            dig.update(tro)
    return dig.hexdigest()


def crea_dir_publico(pth):
    # A restrictive caller umask must not hide directories intended for HTTP access.
    nuevos = []
    des = pth
    while not des.exists():
        nuevos.append(des)
        des = des.parent
    pth.mkdir(parents=True, exist_ok=True)
    for des in reversed(nuevos):
        ajusta_publico(des)
    if not pth.is_symlink():
        ajusta_publico(pth)


def es_solo_lectura(pth):
    """Check the containing filesystem, including files below a mount point."""
    return bool(os.statvfs(pth).f_flag & os.ST_RDONLY)


def ajusta_publico(pth, ejecutable=False, enlace=False):
    """Change only the named managed inode; never follow symlinks or mounted media."""
    info = pth.lstat()
    if stat.S_ISLNK(info.st_mode):
        # lchown changes the link's containing filesystem, not its target's filesystem.
        if enlace and (info.st_uid, info.st_gid) != (uid_pub, gid_pub) and not es_solo_lectura(pth.parent):
            os.chown(pth, uid_pub, gid_pub, follow_symlinks=False)
        return
    if pth.is_dir() and os.path.ismount(pth):
        return
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        return
    if es_solo_lectura(pth):
        return
    modo = 0o755 if stat.S_ISDIR(info.st_mode) or ejecutable else 0o644
    if (info.st_uid, info.st_gid) != (uid_pub, gid_pub):
        os.chown(pth, uid_pub, gid_pub, follow_symlinks=False)
    os.chmod(pth, modo, follow_symlinks=False)


def ajusta_tree(pth):
    """Normalize a writable public tree without crossing links or mount boundaries."""
    if pth.is_symlink() or os.path.ismount(pth) or es_solo_lectura(pth):
        return
    ajusta_publico(pth)
    for arc in pth.iterdir():
        modo = arc.lstat().st_mode
        if stat.S_ISDIR(modo):
            ajusta_tree(arc)
        elif stat.S_ISREG(modo):
            ajusta_publico(arc, ejecutable=bool(modo & 0o111))



def esc_atomic(pth, contenido):
    pth.parent.mkdir(parents=True, exist_ok=True)
    byt = contenido if isinstance(contenido, bytes) else contenido.encode('utf-8')
    with tempfile.NamedTemporaryFile(dir=pth.parent, prefix='.fast-boot-', delete=False) as arc:
        tmp = Path(arc.name)
        try:
            arc.write(byt)
            arc.flush()
            os.fsync(arc.fileno())
            ajusta_publico(tmp)
            os.replace(tmp, pth)
        finally:
            tmp.unlink(missing_ok=True)



def msg_descarga(cfg, rec, etapa, texto, forzar=False):
    nom_arc = rec['filename'] if rec else cfg.stage
    num = f' [{rec["_num"]:02}/{rec["_total"]:02}]' if rec and '_num' in rec else ''
    # Complete, flushed lines stay readable with parallel workers and through tee.
    with mtx_log:
        hora = dt.datetime.now().astimezone().strftime('%H:%M:%S')
        lin = f'[{hora}]{num} [{etapa:8}] {nom_arc} | {texto}'
        if hasattr(cfg, '_log'):
            cfg._log.append(lin)
        if not cfg.quiet or forzar:
            print(lin, file=sys.stderr, flush=True)



def obt_tec_url(cfg):
    return getattr(cfg, 'tec', {}).get('public_url', 'https://tec.1-s.es').rstrip('/')

def pie_licencia():
    return '<footer>CopyLeft 03/2026 · Créditos, Concepto y arquitectura en <a href="https://www.alawise.es/1-s">alawise.es/1-s</a><br>Contenidos publicados bajo licencia <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons CC BY-NC-SA 4.0</a>.</footer>'
