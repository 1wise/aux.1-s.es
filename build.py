#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Build the preview from generate.sh; no operational command is orchestrated."""
import json
import hashlib
from pathlib import Path
import shutil
import tempfile
import zipfile
from types import ModuleType, SimpleNamespace

pth_repo = Path(__file__).resolve().parent
pth_dist = pth_repo / 'dist'
# Load the embedded Python body for packaging, without running its command entry point.
arc_gen = pth_repo / 'generate.sh'
txt_gen = arc_gen.read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
eng = ModuleType('aux_generate')
eng.__file__ = str(arc_gen)
exec(compile(txt_gen, str(arc_gen), 'exec'), eng.__dict__)
pth_iso = pth_repo / 'iso'
if pth_iso.is_dir() and not (pth_iso / 'manifest.json').is_file():
    # A recipe inventory is deliberately distinct from a measured compiled-ISO inventory.
    paquetes_iso = [lin.strip() for lin in (pth_iso / 'packages.txt').read_text().splitlines()
                    if lin.strip() and not lin.lstrip().startswith('#')]
    archivos_iso = [pth_iso / nom for nom in eng.ISO_SOURCE_FILES if (pth_iso / nom).is_file()]
    manifiesto = {'_meta': {'Timestamp': '2026-10-13', 'Version': eng.VERSION, 'Author & Credits': eng.CREDITS},
        'name': 'aux-rescue.iso', 'recipe_version': '5.0.1-dev.5', 'base': 'Fedora 44', 'architecture': 'x86_64',
        'status': 'source recipe; compiled ISO and hardware acceptance not verified by this publication',
        'iso_sha256': None, 'iso_size_bytes': None, 'installed_rpms': None,
        'requested_packages': paquetes_iso, 'requested_count': len(paquetes_iso), 'wifi': True,
        'boot': {'runtime': 'SquashFS + RAM overlay', 'work': 'tmpfs', 'assistant_port': 2222,
                 'consent': 'AUTORIZO', 'observers': ['tty7 read-only tmux', 'tty8 status'],
                 'vpn': 'manual; no private keys or automatic peers'},
        'source_sha256': {arc.relative_to(pth_iso).as_posix(): hashlib.sha256(arc.read_bytes()).hexdigest() for arc in archivos_iso},
        'credits': ['Fedora Project', 'Lorax / livemedia-creator', 'dracut', 'GNU/Linux package authors', '1wise / alawise.es/1-s'],
        'licenses': 'Each component retains its own license; no blanket project license is asserted.',
        'guide': 'iso-guide.html'}
    (pth_iso / 'manifest.json').write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False) + '\n')
pth_nueva = pth_repo / 'iso-assist'
if pth_nueva.is_dir():
    # Inventory before source packaging so every bundle contains the same manifest.
    (pth_nueva / 'manifest.json').write_text(json.dumps({'version': eng.VERSION,
        'status': 'source recipe; this revision not compiled or boot-tested', 'iso_sha256': None,
        'requested_count': len([lin for lin in (pth_nueva / 'packages.txt').read_text().splitlines()
                                if lin.strip() and not lin.lstrip().startswith('#')]),
        'architecture': 'x86_64', 'base': 'Fedora 44',
        'optional_api_terminals': ['GPT Assist / tty4', 'Gemini Assist / tty5'],
        'api_credentials_in_image': False, 'automatic_command_execution': False,
        'bounded_agent_actions': ['diagnostic', 'write_file', 'service_state'],
        'approval_console': '/dev/tty6, menu E', 'persistent_kernel_update': True,
        'persistent_profile': 'combined portable USB; generic ISO remains a RAM Live',
        'support_resume': 'fixed eight-hour case, same equipment, explicit initial consent',
        'live_boot_verified': False,
        'source_sha256': {src.relative_to(pth_nueva).as_posix(): hashlib.sha256(src.read_bytes()).hexdigest()
            for src in sorted(pth_nueva.rglob('*')) if src.is_file() and src.name != 'manifest.json'
            and src.suffix in ('.py', '.sh', '.service', '.conf', '.in', '.txt', '.json', '.md')
            and (len(src.relative_to(pth_nueva).parts) == 1 or src.relative_to(pth_nueva).parts[0] == 'payload')}
        }, indent=2) + '\n')
# Hash the exact portable patches shipped in this revision, including the agent.
pth = pth_repo / 'usb/portable'
dat = json.loads((pth / 'manifest.json').read_text())
dat['_meta']['Version'] = eng.VERSION
dat['case_registry'] = {'implemented_in_sources': True, 'live_verified': False,
    'device_identity': 'USB UUID and hashed DMI UUID after local consent',
    'gateway_history': '/var/lib/aux-cli/history.sqlite3', 'standalone_C': 'manual tracking'}
dat['source_sha256'] = {arc.name: hashlib.sha256(arc.read_bytes()).hexdigest()
    for arc in sorted(pth.iterdir()) if arc.is_file() and arc.name != 'manifest.json'
    and arc.suffix in ('.py', '.md', '.json')}
dat['source_sha256'].update({'live-patch/' + nom: hashlib.sha256(
    (pth_repo / 'iso-assist/payload' / nom).read_bytes()).hexdigest()
    for nom in ('ai.py', 'ai_agent.py', 'assist.py', 'agent.py', 'support_case.py')})
(pth / 'manifest.json').write_text(json.dumps(dat, indent=2) + '\n')
eng.carga_recursos()
raw_urls = (pth_repo / 'url.txt').read_text()
for nom in ['download.sh', 'deploy.sh', 'generate.sh']:
    (pth_repo / nom).chmod(0o755)
cfg = eng.obt_args('generate', pth_repo)
rec_all = eng.obt_catalog(raw_urls)
with tempfile.TemporaryDirectory(prefix='aux-build-') as tmp:
    # Keep published ISO source versions available when distributing a correction.
    pth_ant = Path(tmp) / 'iso-releases'
    pth_ant.mkdir()
    arc_previos = list((pth_dist / 'downloads').glob('*.zip'))
    arc_previos += list((pth_dist / 'downloads').glob('*.zip.sha256'))
    for arc in arc_previos:
        if arc.is_file() and arc.name != 'aux-fast-boot.zip' and arc.name.endswith(('.zip', '.zip.sha256')):
            shutil.copy2(arc, pth_ant / arc.name)
    cfg.output = Path(tmp) / 'html'
    cfg.cache = Path(tmp) / 'cache'
    cfg.output.mkdir()
    cfg.tec_enabled = (pth_repo / 'tec/web/index.php').is_file()
    eng.gen_pages(rec_all, cfg, state='source')
    if pth_dist.exists():
        shutil.rmtree(pth_dist)
    shutil.copytree(cfg.output, pth_dist)
    for arc in pth_ant.iterdir():
        shutil.copy2(arc, pth_dist / 'downloads' / arc.name)
    # PHP is used on the server; the hosted preview serves the same static HTML.
    for arc in pth_dist.rglob('*.php'):
        arc.unlink()
    for nom in ['index.html', 'index.php', 'index-aux.php', 'index-pxe.html', 'cli.html', 'cli-all.html', 'menu.ipxe',
                'sitemaps.xml', 'sitemaps-aux.xml', 'sitemaps-pxe.xml', 'catalog.json', 'SHA256SUMS', 'contents.html',
                'operations.html', 'chroot.html', 'chroot-all.html', 'iso-guide.html', 'tec-502.html', 'usb-guide.html', 'debian-deploy.html', 'architectures.html', 'alpine-guide.html', 'configuration.html', 'next-key.html', 'release-6.html', 'work.html']:
        shutil.copy2(cfg.output / nom, pth_repo / nom)
    shutil.copytree(cfg.output / 'files', pth_repo / 'files', dirs_exist_ok=True)
    shutil.copytree(cfg.output / 'assets', pth_repo / 'assets', dirs_exist_ok=True)
    shutil.copy2(cfg.output / 'downloads/DEPLOYMENT.md', pth_repo / 'DEPLOYMENT.md')
arc_site = pth_repo / 'site.json'
origin = json.loads(arc_site.read_text())['origin'] if arc_site.exists() else cfg.base_url
(pth_dist / 'sitemaps.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + origin.rstrip('/') + '/</loc></url></urlset>\n')
(pth_dist / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + origin.rstrip('/') + '/sitemaps.xml\n')
release = pth_dist / 'downloads' / ('aux-pxe-' + eng.VERSION + '.zip')
shutil.copy2(pth_dist / 'downloads/aux-fast-boot.zip', release)
release.with_suffix('.zip.sha256').write_text(hashlib.sha256(release.read_bytes()).hexdigest() + '  ' + release.name + '\n')
pth_tech = pth_repo / 'tec'
if pth_tech.is_dir():
    # TEC deploys independently; only its static overview belongs in the Site.
    tech_release = pth_dist / 'downloads' / ('tec-platform-' + eng.VERSION + '.zip')
    with zipfile.ZipFile(tech_release, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for src in sorted(pth_tech.rglob('*')):
            if src.is_file() and src.name != 'php-fpm.conf.example' and src.suffix in ('.php', '.css', '.html', '.md', '.py', '.example', '.ttf', '.js', '.cjs', '.json', '.txt'):
                archive.write(src, src.relative_to(pth_tech).as_posix())
        archive.writestr('nginx.conf.example', eng.configura_ejemplo('nginx/aux-pxe-tec.conf.example', (pth_repo / 'nginx/aux-pxe-tec.conf.example').read_text(), cfg))
        archive.writestr('php-fpm.conf.example', eng.configura_ejemplo('tec/php-fpm.conf.example', (pth_tech / 'php-fpm.conf.example').read_text(), cfg))
        archive.write(pth_repo / 'fast-boot.json', 'fast-boot.json.example')
        for nom in ('RELEASE-6.3.md', 'INSTALL-6.3.md'):
            archive.write(pth_repo / nom, nom)
    tech_release.with_suffix('.zip.sha256').write_text(hashlib.sha256(tech_release.read_bytes()).hexdigest() + '  ' + tech_release.name + '\n')
    shutil.copy2(pth_tech / 'README.md', pth_dist / 'downloads/tec-README.md')
    shutil.copy2(pth_tech / 'MIGRATION-5.0.2.md', pth_dist / 'downloads/MIGRATION-5.0.2.md')
    (pth_dist / 'tec').mkdir()
    vista_tec = (pth_tech / 'preview.html').read_text().replace('5.1.0', eng.VERSION)
    vista_tec = vista_tec.replace('</main>', '<section><h2>6.3 · Agentes y pasarela SSH web</h2><p>CLI transporta SSH humano; aux-exec funciona dentro de la ISO, con aprobación física. Alta TOTP desde la cuenta TEC. Fuentes de pruebas.</p><p><a href="../release-6.html">Alcance, paquetes y checklist</a></p></section></main>')
    (pth_dist / 'tec/index.html').write_text(vista_tec)
    shutil.copy2(pth_tech / 'web/theme.css', pth_dist / 'tec/theme.css')
    shutil.copy2(pth_tech / 'web/pxe-bits.ttf', pth_dist / 'tec/pxe-bits.ttf')
pth_iso = pth_repo / 'iso'
if pth_iso.is_dir():
    # Distribute the editable ISO recipe independently; exclude build/runtime data.
    iso_release = pth_dist / 'downloads/tec-fedora44-rescue-5.0.1-dev.5-sources.zip'
    if not iso_release.is_file():
        with zipfile.ZipFile(iso_release, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for rel in [Path(nom) for nom in eng.ISO_SOURCE_FILES + ['manifest.json']]:
                src = pth_iso / rel
                if src.is_file():
                    archive.write(src, rel.as_posix())
        iso_release.with_suffix('.zip.sha256').write_text(hashlib.sha256(iso_release.read_bytes()).hexdigest() + '  ' + iso_release.name + '\n')
    shutil.copy2(pth_iso / 'README.md', pth_dist / 'downloads/iso-README.md')
    shutil.copy2(pth_iso / 'packages.txt', pth_dist / 'downloads/iso-packages.txt')
    (pth_dist / 'iso').mkdir()
    shutil.copy2(pth_iso / 'preview.html', pth_dist / 'iso/index.html')
print(f'Built {len(rec_all)} source resources and three independent command sources.')
for folder, name in [('cli', 'aux-cli-'), ('iso-assist', 'aux-assist-')]:
    release = pth_dist / 'downloads' / (name + eng.VERSION + ('-sources' if folder == 'iso-assist' else '') + '.zip')
    with zipfile.ZipFile(release, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for src in sorted((pth_repo / folder).rglob('*')):
            if src.is_file() and '__pycache__' not in src.parts and src.suffix in ('.py', '.md', '.txt', '.json', '.conf', '.in', '.service', '.example', '.sh'):
                archive.write(src, src.relative_to(pth_repo / folder).as_posix())
        if folder == 'iso-assist':
            for src in sorted((pth_repo / 'usb/portable').iterdir()):
                if src.is_file() and src.suffix in ('.py', '.json', '.md'):
                    archive.write(src, 'portable/' + src.name)
        archive.write(pth_repo / 'RELEASE-6.md', 'RELEASE-6.md')
        for nom in ('RELEASE-6.3.md', 'CHECKLIST-6.3.json', 'TEST-6.3.md', 'INSTALL-6.3.md'):
            archive.write(pth_repo / nom, nom)
        archive.write(pth_repo / 'fast-boot.json', 'fast-boot.json.example')
    release.with_suffix('.zip.sha256').write_text(hashlib.sha256(release.read_bytes()).hexdigest() + '  ' + release.name + '\n')
release = pth_dist / 'downloads' / ('aux-portable-' + eng.VERSION + '-kit.zip')
with zipfile.ZipFile(release, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for src in sorted((pth_repo / 'usb/portable').iterdir()):
        if src.is_file() and src.suffix in ('.py', '.json', '.md'):
            archive.write(src, src.name)
    for nom in ('ai.py', 'ai_agent.py', 'assist.py', 'agent.py', 'support_case.py'):
        archive.write(pth_repo / 'iso-assist/payload' / nom, 'live-patch/' + nom)
release.with_suffix('.zip.sha256').write_text(hashlib.sha256(release.read_bytes()).hexdigest() + '  ' + release.name + '\n')
suite = pth_dist / 'downloads' / ('aux-suite-' + eng.VERSION + '.zip')
with zipfile.ZipFile(suite, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name in ['aux-pxe-' + eng.VERSION, 'tec-platform-' + eng.VERSION,
                 'aux-cli-' + eng.VERSION, 'aux-assist-' + eng.VERSION + '-sources',
                 'aux-portable-' + eng.VERSION + '-kit']:
        for suffix in ['.zip', '.zip.sha256']:
            archive.write(pth_dist / 'downloads' / (name + suffix), name + suffix)
    for name in ['RELEASE-6.3.md', 'CHECKLIST-6.3.json', 'TEST-6.3.md', 'INSTALL-6.3.md', 'install-web.py']:
        archive.write(pth_repo / name, name)
    archive.write(pth_repo / 'tec/REGISTRY.md', 'REGISTRY-6.3.md')
    archive.writestr('SHA256SUMS', ''.join(hashlib.sha256(archive.read(nom)).hexdigest() + '  ' + nom + '\n'
                                        for nom in archive.namelist()))
suite.with_suffix('.zip.sha256').write_text(hashlib.sha256(suite.read_bytes()).hexdigest() + '  ' + suite.name + '\n')
