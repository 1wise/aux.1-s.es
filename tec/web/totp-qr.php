<?php
/** Timestamp: 2026-11-09 | Version: 7.0.0-dev.2
 * Author & Credits: https://www.alawise.es/1-s
 * Keep enrollment material on the authenticated server, outside command arguments.
 */
declare(strict_types=1);
if (!defined('AUX_ASSIST_ENTRY')) { http_response_code(404); exit; }

function totp_qr_svg(string $correo, string $sem, string $sys_bin='/usr/bin/qrencode'): string {
    if (!preg_match('/^[A-Z2-7]{16,128}$/D', $sem)) {
        throw new InvalidArgumentException('Secreto de inscripción inválido.');
    }
    $uri = 'otpauth://totp/'.rawurlencode('AUX:'.$correo).'?secret='.$sem.'&issuer=AUX&algorithm=SHA1&digits=6&period=30';
    $proc = proc_open([$sys_bin,'-t','SVG','-o','-'],
        [0=>['pipe','r'],1=>['pipe','w'],2=>['pipe','w']], $can);
    if (!is_resource($proc)) throw new RuntimeException('QR no disponible; usar la clave manual.');
    fwrite($can[0], $uri); fclose($can[0]);
    $svg = stream_get_contents($can[1], 262144); fclose($can[1]);
    stream_get_contents($can[2], 16384); fclose($can[2]);
    if (proc_close($proc)!==0 || !str_contains($svg,'<svg')) {
        throw new RuntimeException('QR no disponible; usar la clave manual.');
    }
    return $svg;
}
