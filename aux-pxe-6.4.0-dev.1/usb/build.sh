#!/usr/bin/env bash
# Timestamp: 2026-10-13 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# iPXE project and source: https://ipxe.org | https://github.com/ipxe/ipxe
# Build an optional USB client; server download/deploy/generate remain independent.
set -Eeuo pipefail

pth_app="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pth_src="${pth_app}/.usb-build/ipxe"
pth_out="${pth_app}/usb"
rev_ipxe="c86730a30547823e73a363d903a1510a4664a9b1"
url_menu=""
num_jobs=""
pth_cfg="${pth_app}/fast-boot.json"

while (($#)); do
    case "$1" in
        --config) pth_cfg="${2:?Missing configuration path}"; shift 2 ;;
        --source-dir) pth_src="${2:?Missing source directory}"; shift 2 ;;
        --output-dir) pth_out="${2:?Missing output directory}"; shift 2 ;;
        --menu-url) url_menu="${2:?Missing menu URL}"; shift 2 ;;
        --revision) rev_ipxe="${2:?Missing full commit SHA}"; shift 2 ;;
        --jobs) num_jobs="${2:?Missing job count}"; shift 2 ;;
        --help|-h)
            cat <<'HELP'
Usage: bash usb/build.sh [OPTIONS]
  --config PATH      Central fast-boot.json; defaults beside project sources
  --menu-url URL     Override the menu URL derived from pxe_url
  --source-dir PATH  Dedicated iPXE checkout, pinned to the requested commit
  --output-dir PATH  Image, bootstrap, build metadata and checksums
  --revision SHA    Full upstream commit SHA
  --jobs N          Override the compiler jobs from central configuration
Requires Git, Bash, Python 3, GCC, binutils, make, Perl, liblzma headers,
mtools, xorriso and GRUB rescue tools/modules for BIOS + x86_64 UEFI.
The custom UEFI executable is unsigned. This command never flashes a USB.
HELP
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
done

# Explicit build flags override central deployment settings.
if [[ -z "${url_menu}" ]]; then
    url_menu="$(python3 - "${pth_cfg}" <<'PYCFG'
import json, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
print(cfg.get('pxe_url', 'http://pxe.1-s.es').rstrip('/') + '/menu.ipxe')
PYCFG
)"
fi
if [[ -z "${num_jobs}" ]]; then
    num_jobs="$(python3 - "${pth_cfg}" <<'PYCFG'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text()).get('jobs', 4))
PYCFG
)"
fi

[[ "${rev_ipxe}" =~ ^[0-9a-f]{40}$ ]] || { printf 'A full upstream commit SHA is required.\n' >&2; exit 2; }
[[ "${num_jobs}" =~ ^[1-9][0-9]*$ ]] || { printf 'Jobs must be a positive integer.\n' >&2; exit 2; }
# iPXE expands settings and command operators: accept only a literal, single-token URL.
python3 - "${url_menu}" <<'PY'
import re, sys
from urllib.parse import urlsplit
url = sys.argv[1]
parts = urlsplit(url)
if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
    raise SystemExit('Menu must be a public HTTP(S) URL without credentials')
if re.search(r'[\s\x00-\x1f\x7f$;|&<>\\"\']', url):
    raise SystemExit('Menu URL contains unsupported script characters; percent-encode them')
PY

for cmd in git gcc ld objcopy make perl mformat mcopy xorriso; do
    command -v "${cmd}" >/dev/null || { printf 'Missing dependency: %s\n' "${cmd}" >&2; exit 1; }
done
cmd_grub="${AUX_GRUB_MKRESCUE:-}"
if [[ -z "${cmd_grub}" ]]; then
    cmd_grub="$(command -v grub2-mkrescue || command -v grub-mkrescue || true)"
fi
[[ -x "${cmd_grub}" ]] || { printf 'Missing dependency: grub2-mkrescue / grub-mkrescue\n' >&2; exit 1; }
mkdir -p -- "${pth_out}" "$(dirname -- "${pth_src}")"
pth_out="$(cd -- "${pth_out}" && pwd)"
if [[ ! -d "${pth_src}/.git" ]]; then
    [[ ! -e "${pth_src}" ]] || { printf 'Source path already exists without Git: %s\n' "${pth_src}" >&2; exit 1; }
    printf '[SOURCE] Downloading the official iPXE source\n'
    git clone --depth 1 https://github.com/ipxe/ipxe.git "${pth_src}"
fi
pth_src="$(cd -- "${pth_src}" && pwd)"
[[ -z "$(git -C "${pth_src}" status --porcelain --untracked-files=no)" ]] || {
    printf 'Tracked source changes found; use a dedicated clean checkout.\n' >&2; exit 1;
}
if ! git -C "${pth_src}" cat-file -e "${rev_ipxe}^{commit}" 2>/dev/null; then
    git -C "${pth_src}" fetch --depth 1 origin "${rev_ipxe}"
fi
git -C "${pth_src}" checkout --detach "${rev_ipxe}"
export SOURCE_DATE_EPOCH="$(git -C "${pth_src}" show -s --format=%ct "${rev_ipxe}")"

sed "s|@@MENU_URL@@|${url_menu}|g" "${pth_app}/usb/bootstrap.ipxe.in" > "${pth_out}/bootstrap.ipxe"
mkdir -p "${pth_src}/src/config/local/aux"
# Avoid rebuilding every object when the existing local configuration is identical.
for nom in general.h console.h colour.h; do
    cmp -s "${pth_app}/usb/${nom}" "${pth_src}/src/config/local/aux/${nom}" || \
        cp "${pth_app}/usb/${nom}" "${pth_src}/src/config/local/aux/${nom}"
done
printf '[BUILD] BIOS client with HTTP/HTTPS and an embedded bootstrap\n'
make -C "${pth_src}/src" -j "${num_jobs}" bin/ipxe.lkrn CONFIG=aux EMBED="${pth_out}/bootstrap.ipxe"
printf '[BUILD] x86_64 UEFI client with the same bootstrap\n'
make -C "${pth_src}/src" -j "${num_jobs}" bin-x86_64-efi/ipxe.efi CONFIG=aux EMBED="${pth_out}/bootstrap.ipxe"
printf '[IMAGE] Creating the hybrid GRUB USB image (visible menu, 5 seconds)\n'
python3 "${pth_app}/usb/grub-image.py" --mkrescue "${cmd_grub}" \
    --bios "${pth_src}/src/bin/ipxe.lkrn" --efi "${pth_src}/src/bin-x86_64-efi/ipxe.efi" \
    --config "${pth_app}/usb/grub.cfg" --output "${pth_out}/aux-ipxe-usb.img.tmp"
chmod 644 "${pth_out}/aux-ipxe-usb.img.tmp" "${pth_out}/bootstrap.ipxe"
mv -- "${pth_out}/aux-ipxe-usb.img.tmp" "${pth_out}/aux-ipxe-usb.img"

python3 - "${pth_out}" "${pth_src}" "${rev_ipxe}" "${url_menu}" <<'PY'
import hashlib, json, struct, sys
from pathlib import Path
pth_out, pth_src = map(Path, sys.argv[1:3])
image = pth_out / 'aux-ipxe-usb.img'
header = image.read_bytes()[:512]
if header[510:512] != b'\x55\xaa':
    raise SystemExit('USB image has no valid MBR boot signature')
entries = [struct.unpack_from('<B3sB3sII', header, 446 + i * 16) for i in range(4)]
if not any(ent[4] and ent[5] for ent in entries):
    raise SystemExit('USB image has no nonempty hybrid partition')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
data = {'version': '6.3.0-dev.1', 'credits': 'https://www.alawise.es/1-s',
        'ipxe_project': 'https://ipxe.org', 'source_repository': 'https://github.com/ipxe/ipxe',
        'source_commit': sys.argv[3], 'menu_url': sys.argv[4],
        'firmware': ['BIOS', 'UEFI x86_64'], 'uefi_signed': False,
        'format': 'GRUB hybrid ISO/USB', 'grub_timeout_seconds': 5,
        'protocols': ['HTTP', 'HTTPS'], 'image': image.name, 'size': image.stat().st_size,
        'sha256': sha(image), 'bootstrap_sha256': sha(pth_out / 'bootstrap.ipxe'),
        'bios_sha256': sha(pth_src / 'src/bin/ipxe.lkrn'),
        'uefi_sha256': sha(pth_src / 'src/bin-x86_64-efi/ipxe.efi')}
(pth_out / 'build-info.json').write_text(json.dumps(data, indent=2) + '\n')
(pth_out / 'SHA256SUMS').write_text(''.join(f'{sha(pth_out / name)}  {name}\n' for name in
    ['aux-ipxe-usb.img', 'bootstrap.ipxe', 'build-info.json']))
for name in ['build-info.json', 'SHA256SUMS']:
    (pth_out / name).chmod(0o644)
print(f'[DONE] {image} | {image.stat().st_size:,} bytes | SHA256 {data["sha256"]}')
PY
