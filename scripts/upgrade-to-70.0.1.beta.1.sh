#!/usr/bin/env bash
# Timestamp: 2026-11-15 | Version: 70.0.1.beta.1
# Author & Credits: https://www.alawise.es/1-s
# Migrate an extracted AUX 7.0.0-beta.20 source tree to clean v70.0.1.beta.1.
set -Eeuo pipefail

pth_src="${1:-.}"
cd -- "${pth_src}"

if [[ ! -f "generate.sh" || ! -d "auxlib" ]]; then
    echo "ERROR: Run this script inside the root of the AUX source tree." >&2
    exit 1
fi

echo "[1/5] Purging legacy 5.x/6.x/beta19 historical docs and obsolete verifiers..."
rm -f \
    CHECKLIST-6.json CHECKLIST-6.1.json CHECKLIST-6.2.json CHECKLIST-6.3.json CHECKLIST-6.4.json \
    INSTALL-6.2.md INSTALL-6.3.md INSTALL-6.4.md \
    RELEASE-6.md RELEASE-6.1.md RELEASE-6.2.md RELEASE-6.3.md RELEASE-6.4.md RELEASE-7.md \
    TEST-6.1.md TEST-6.2.md TEST-6.3.md TEST-6.4.md \
    verify-v6.py verify-v61.py verify-v62.py verify-v63.py verify-v64.py \
    docs/BASELINE-19.json docs/DEPLOY-BETA1.md docs/REBUILD-FROM-19.md \
    docs/terminal-beta1-results.json \
    assist/AGENT-6.2.md assist/AGENT-6.3.md assist/CHECKLIST-6.4.json \
    assist/INSTALL-6.4.md assist/RELEASE-6.md assist/RELEASE-6.4.md assist/TEST-6.4.md \
    iso-assist/AGENT-6.2.md iso-assist/AGENT-6.3.md \
    usb/USB-6.1.md usb/USB-6.2.md usb/USB-6.3.md \
    tec/MIGRATION-5.0.2.md tec/MIGRATION-5.1.0.md
rm -rf docs/edition-7-dev1

echo "[2/5] Unifying version string to 70.0.1.beta.1 across all headers and modules..."
printf '70.0.1.beta.1\n' > VERSION

python3 - <<'PY'
from pathlib import Path
import re

ver_new = '70.0.1.beta.1'
root = Path('.').resolve()

# Update version literals and headers across Python, Bash, JS, Markdown, and JSON files.
for pth in sorted(root.rglob('*')):
    if not pth.is_file() or '.git' in pth.parts or '__pycache__' in pth.parts:
        continue
    if pth.suffix in ('.py', '.sh', '.cjs', '.js', '.md', '.json', '.in', '.conf', '.htaccess') or pth.name in (
        'aux', 'aux-setup', 'aux-profile', 'aux-catalog', 'aux-enter',
        'aux-assist', 'aux-tools', 'aux-images', 'aux-config', 'aux-release'
    ):
        try:
            txt = pth.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        orig = txt
        txt = re.sub(r'Version:\s*7\.0\.0-beta\.\d+', f'Version: {ver_new}', txt)
        txt = re.sub(r'"Version":\s*"7\.0\.0-beta\.\d+"', f'"Version": "{ver_new}"', txt)
        txt = re.sub(r"VERSION\s*=\s*'7\.0\.0-beta\.\d+'", f"VERSION = '{ver_new}'", txt)
        txt = re.sub(r'"version":\s*"7\.0\.0-beta\.\d+"', f'"version": "{ver_new}"', txt)
        if txt != orig:
            pth.write_text(txt, encoding='utf-8')
PY

echo "[3/5] Patching generate.sh (--input-root symlink resolution & pruned legacy list)..."
python3 - <<'PY'
from pathlib import Path

pth = Path('generate.sh')
txt = pth.read_text(encoding='utf-8')

# Fix 1: Allow --input-root symlinked files in obt_par and arc_unidad so aux-release generate
# keeps pxe_ready=True for all deployed trees. Use ''' outer quotes to avoid colliding with """.
old_block = '''def obt_par(pth_tree, pares):
  if not pth_tree.is_dir():
    return None
  for pat_ker, pat_ini in pares:
    ker_all = sorted(pth_tree.glob(pat_ker))
    ini_all = sorted(pth_tree.glob(pat_ini))
    for ker in ker_all:
      for ini in ini_all:
        if ker.is_file() and ini.is_file() and ker.parent == ini.parent and ker.stat().st_size and ini.stat().st_size and ker.resolve().is_relative_to(pth_tree.resolve()) and ini.resolve().is_relative_to(pth_tree.resolve()):
          return ker, ini
  return None


def arc_unidad(pth_tree, nom):
  """Resolve original media paths without permitting escapes from the public unit."""
  pth = pth_tree / nom
  return pth if nom and not Path(nom).is_absolute() and pth.resolve().is_relative_to(pth_tree.resolve()) and arc_presente(pth) else None'''

new_block = '''def ruta_permitida(pth, pth_tree):
  """Accept in-unit files and verified --input-root symlinks into cache/RAM/source."""
  real = pth.resolve()
  if real.is_relative_to(pth_tree.resolve()):
    return True
  cfg = globals().get('cfg_activa')
  return bool(cfg and getattr(cfg, 'input_root', None) and any(
      real.is_relative_to(r) for r in getattr(cfg, 'input_read_roots', [])))


def obt_par(pth_tree, pares):
  if not pth_tree.is_dir():
    return None
  for pat_ker, pat_ini in pares:
    ker_all = sorted(pth_tree.glob(pat_ker))
    ini_all = sorted(pth_tree.glob(pat_ini))
    for ker in ker_all:
      for ini in ini_all:
        if ker.is_file() and ini.is_file() and ker.parent == ini.parent and ker.stat().st_size and ini.stat().st_size and ruta_permitida(ker, pth_tree) and ruta_permitida(ini, pth_tree):
          return ker, ini
  return None


def arc_unidad(pth_tree, nom):
  """Resolve original media paths without permitting escapes from the public unit."""
  pth = pth_tree / nom
  return pth if nom and not Path(nom).is_absolute() and ruta_permitida(pth, pth_tree) and arc_presente(pth) else None'''

if old_block in txt:
    txt = txt.replace(old_block, new_block, 1)

# Fix 2: Clean removed legacy 6.x files from carga_recursos() list in generate.sh
for obs in [
    "'RELEASE-6.md', ", "'CHECKLIST-6.json', ", "'RELEASE-6.1.md', ", "'CHECKLIST-6.1.json', ", "'TEST-6.1.md', ",
    "'RELEASE-6.2.md', ", "'CHECKLIST-6.2.json', ", "'TEST-6.2.md', ", "'INSTALL-6.2.md', ",
    "'RELEASE-6.3.md', ", "'CHECKLIST-6.3.json', ", "'TEST-6.3.md', ", "'INSTALL-6.3.md', ",
    "'verify-v6.py', ", "'verify-v61.py', ", "'verify-v62.py', ", "'verify-v63.py', ",
    "'usb/USB-6.1.md', ", "'usb/USB-6.2.md', ", "'usb/USB-6.3.md'",
    "'RELEASE-6.4.md', ", "'CHECKLIST-6.4.json', ", "'TEST-6.4.md', ", "'INSTALL-6.4.md', ", "'verify-v64.py'",
    "'tec/MIGRATION-5.1.0.md', ", "'tec/MIGRATION-5.0.2.md', "
]:
    txt = txt.replace(obs, "")

pth.write_text(txt, encoding='utf-8')
PY

echo "[4/5] Cleaning legacy 6.x file references in install-web.py and iso-assist/manifest.json..."
python3 - <<'PY'
from pathlib import Path
import hashlib, json

inst = Path('install-web.py')
if inst.is_file():
    txt = inst.read_text(encoding='utf-8')
    for obs in [
        "'RELEASE-6.md', ", "'CHECKLIST-6.json', ", "'RELEASE-6.1.md', ", "'CHECKLIST-6.1.json', ",
        "'TEST-6.1.md', ", "'RELEASE-6.3.md', ", "'CHECKLIST-6.3.json', ", "'TEST-6.3.md', ", "'INSTALL-6.3.md', ",
        "'RELEASE-6.4.md', ", "'CHECKLIST-6.4.json', ", "'TEST-6.4.md', ", "'INSTALL-6.4.md'"
    ]:
        txt = txt.replace(obs, "")
    inst.write_text(txt, encoding='utf-8')

man_pth = Path('iso-assist/manifest.json')
if man_pth.is_file():
    dat = json.loads(man_pth.read_text(encoding='utf-8'))
    dat['version'] = '70.0.1.beta.1'
    new_hashes = {}
    for rel in sorted(dat.get('source_sha256', {})):
        arc = Path('iso-assist') / rel
        if arc.is_file():
            new_hashes[rel] = hashlib.sha256(arc.read_bytes()).hexdigest()
    dat['source_sha256'] = new_hashes
    man_pth.write_text(json.dumps(dat, indent=2) + '\n', encoding='utf-8')
PY

echo "[5/5] Regenerating root SHA256SUMS manifest..."
python3 - <<'PY'
from pathlib import Path
import hashlib

root = Path('.').resolve()
excl = {'dist', '.git', '.openai', '.venv', '__pycache__', 'state'}
files = [
    p for p in sorted(root.rglob('*'))
    if p.is_file() and not set(p.relative_to(root).parts) & excl
    and p.suffix != '.pyc' and p.name != 'SHA256SUMS'
]
lines = [
    hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(root).as_posix()
    for p in files
]
(root / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f"SHA256SUMS updated with {len(lines)} verified files.")
PY

echo "Done! Tree is now at v70.0.1.beta.1."
