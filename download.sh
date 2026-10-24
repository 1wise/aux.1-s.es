#!/usr/bin/env bash
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# The task body lives here so the command can be reviewed and run on its own.
set -Eeuo pipefail
pth_app="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "${pth_app}" "$@" <<'AUXPY'
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Download only: URL list to persistent cache, with verbose transfer progress."""
import sys
from pathlib import Path

pth_app = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else Path(__file__).resolve().parent
sys.path.insert(0, str(pth_app / 'src'))
from common import *


def ejec_curl(cmd, rec, cfg, reanudar=False):
    """Relay curl's carriage-return progress meter as labelled terminal lines."""
    lis_err = []
    tms_ult = 0.0
    txt_ult = None

    def procesa_linea(raw):
        nonlocal tms_ult, txt_ult
        lin = raw.decode('utf-8', errors='replace').strip()
        if not lin or lin.startswith(('% Total', 'Dload  Upload')):
            return
        cols = lin.split()
        if len(cols) >= 12 and cols[0].isdigit() and cols[2].isdigit() and cols[4].isdigit():
            # Curl's byte units are 1024-based. A resumed meter covers the remaining transfer.
            pct = min(100, int(cols[2]))
            n_bar = pct * 20 // 100
            bar = '#' * n_bar + '.' * (20 - n_bar)
            txt = (f'[{bar}] {pct:3}% | {cols[3]}/{cols[1]} | {cols[11]}/s | '
                   f'ETA {cols[10]}' + (' | remaining transfer' if reanudar else ''))
            tms_act = time.monotonic()
            if txt != txt_ult and (tms_act - tms_ult >= 2 or cols[2] == '100'):
                msg_descarga(cfg, rec, 'PROGRESS', txt)
                tms_ult, txt_ult = tms_act, txt
            return
        lis_err.append(lin)
        del lis_err[:-8]
        msg_descarga(cfg, rec, 'CURL', lin, forzar=True)

    if cfg.quiet:
        cmd += ['--silent']
    with subprocess.Popen(cmd + [rec['url']], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          bufsize=0, env={**os.environ, 'LC_ALL': 'C'}) as proc:
        buf = b''
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                break
            buf += chunk
            parts = re.split(br'[\r\n]+', buf)
            buf = parts.pop()
            for raw in parts:
                procesa_linea(raw)
        if buf:
            procesa_linea(buf)
        return proc.wait(), '\n'.join(lis_err)



def sin_descarga(rec, cfg, sumas):
    arc_cac = cfg.cache / rec['filename']
    tmp = cfg.cache / (rec['filename'] + '.part')
    arc_cab = cfg.cache / (rec['filename'] + '.part.headers')
    es_valid = arc_valido(arc_cac, rec['filename'])
    error = None
    if cfg.refresh or not es_valid:
        msg_descarga(cfg, rec, 'START', 'Downloading from ' + urlsplit(rec['url']).netloc)
        cmd = ['curl', '--fail', '--location', '--show-error', '--retry', '3',
               '--connect-timeout', '20', '--speed-limit', '1024', '--speed-time', '60',
               '--proto', '=http,https', '--proto-redir', '=http,https', '--output', str(tmp)]
        # Resume only with a server validator so a changed upstream cannot splice two images.
        validator = None
        if tmp.exists() and arc_cab.exists():
            cabs = arc_cab.read_text(errors='replace')
            etags = re.findall(r'^etag:\s*(.+)$', cabs, re.I | re.M)
            mods = re.findall(r'^last-modified:\s*(.+)$', cabs, re.I | re.M)
            validator = (etags or mods or [None])[-1]
        if tmp.exists() and validator:
            msg_descarga(cfg, rec, 'RESUME', f'{tmp.stat().st_size:,} bytes already saved; validating the upstream with If-Range')
            cmd += ['--continue-at', '-', '--header', 'If-Range: ' + validator.strip()]
        elif tmp.exists():
            msg_descarga(cfg, rec, 'RESTART', 'Partial file has no server validator; starting a fresh download')
            tmp.unlink()
        cmd += ['--dump-header', str(arc_cab)]
        cod_ret, txt_err = ejec_curl(cmd, rec, cfg, reanudar=bool(validator))
        if cod_ret == 0 and arc_valido(tmp, rec['filename']):
            msg_descarga(cfg, rec, 'VERIFY', f'{tmp.stat().st_size:,} bytes received; calculating SHA-256')
            dig = obt_sha(tmp)
            if rec['filename'] in sumas and sumas[rec['filename']] != dig:
                error = f'Trusted checksum mismatch: expected {sumas[rec["filename"]]}, obtained {dig}'
                tmp.unlink(missing_ok=True)
            else:
                ajusta_publico(tmp)
                os.replace(tmp, arc_cac)
                es_valid = True
                rec['sha256'] = dig
                rec['status'] = 'downloaded'
                msg_descarga(cfg, rec, 'DONE', f'{arc_cac.stat().st_size:,} bytes saved; ' + ('trusted checksum matched' if rec['filename'] in sumas else 'SHA-256 recorded'))
        else:
            error = f'curl exited with code {cod_ret}' + (': ' + txt_err if txt_err else '') if cod_ret else 'Download returned an invalid payload'
            # A completed invalid response must not be resumed as if it were a partial image.
            if cod_ret in (0, 33, 36):
                tmp.unlink(missing_ok=True)
        if error:
            msg_descarga(cfg, rec, 'ERROR', error, forzar=True)
            if tmp.exists():
                msg_descarga(cfg, rec, 'PARTIAL', f'{tmp.stat().st_size:,} bytes retained for a later resume', forzar=True)
    if es_valid:
        ajusta_publico(arc_cac)
        rec['size'] = arc_cac.stat().st_size
        if not rec['sha256']:
            msg_descarga(cfg, rec, 'VERIFY', f'Checking cached file: {rec["size"]:,} bytes; calculating SHA-256')
        rec['sha256'] = rec['sha256'] or obt_sha(arc_cac)
        if rec['filename'] in sumas and sumas[rec['filename']] != rec['sha256']:
            rec['status'] = 'checksum-failed'
            rec['error'] = f'Cached payload differs from trusted checksum: expected {sumas[rec["filename"]]}, obtained {rec["sha256"]}'
            msg_descarga(cfg, rec, 'ERROR', rec['error'], forzar=True)
            return rec
        if not error:
            # Keep failed-refresh partials, but clear obsolete bytes after verified success.
            tmp.unlink(missing_ok=True)
            arc_cab.unlink(missing_ok=True)
        if rec['status'] != 'downloaded':
            rec['status'] = 'cached' if not error else 'cached-after-error'
            msg_descarga(cfg, rec, 'CACHE', f'Reusing {rec["size"]:,} bytes' + (' from the previous valid copy after the failed refresh' if error else ''))
    else:
        rec['status'] = 'failed'
    if error:
        rec['error'] = error
    return rec



def main():
    cfg = obt_args('download', pth_app)
    if not cfg.dry_run:
        inicia_informe(cfg)
    rec_all = obt_catalog(Path(cfg.url_file).read_text(), cfg.only)
    if cfg.dry_run:
        muestra_plan(cfg, rec_all)
        return 0
    if not shutil.which('curl'):
        raise ValueError('Missing dependency: curl')
    sumas = obt_sumas(cfg)
    crea_dir_publico(cfg.cache)
    tms_ini = time.monotonic()
    with bloq_cache(cfg):
        for num, rec in enumerate(rec_all, 1):
            rec.update(_num=num, _total=len(rec_all))
        msg_descarga(cfg, None, 'PLAN', f'{len(rec_all)} downloads | cache={cfg.cache}')
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.jobs) as pool:
            def descarga_segura(rec):
                try:
                    return sin_descarga(rec, cfg, sumas)
                except (ValueError, OSError, subprocess.CalledProcessError) as exc:
                    rec.update(status='failed', error=describe_error(exc), error_stage='download')
                    msg_descarga(cfg, rec, 'ERROR', rec['error'], forzar=True)
                    return rec
            rec_all = list(pool.map(descarga_segura, rec_all))
        # Separate list runs share one cache; preserve the other list's source labels.
        arc_dat = cfg.cache / 'downloads.json'
        prev = json.loads(arc_dat.read_text()).get('resources', []) if arc_dat.is_file() else []
        rec_dat = {rec['filename']: rec for rec in prev if isinstance(rec, dict) and rec.get('filename')}
        rec_dat.update({rec['filename']: {k: v for k, v in rec.items() if not k.startswith('_')}
                        for rec in rec_all})
        dat = {'version': VERSION, 'stage': 'download',
               'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'resources': [rec_dat[nom] for nom in sorted(rec_dat)]}
        esc_atomic(cfg.cache / 'downloads.json', json.dumps(dat, indent=2) + '\n')
        return fin_tarea(cfg, rec_all, tms_ini)


if __name__ == '__main__':
    raise SystemExit(ejecuta_main(main))
AUXPY
