<?php
/** Timestamp: 2026-11-09 | Version: 7.0.0-dev.2
 * Author & Credits: https://www.alawise.es/1-s
 * Exercise the real local encoder without writing enrollment secrets to argv.
 */
declare(strict_types=1);
define('AUX_ASSIST_ENTRY', true);
require __DIR__.'/web/totp-qr.php';
$sys_bin=$argv[1]??'/usr/bin/qrencode';
$svg=totp_qr_svg('fixture@example.test','JBSWY3DPEHPK3PXP',$sys_bin);
if (!str_contains($svg,'<svg') || strlen($svg)<500) throw new RuntimeException('QR SVG missing.');
try {
    totp_qr_svg('fixture@example.test',"bad\nseed",$sys_bin);
    throw new RuntimeException('Invalid seed was accepted.');
} catch (InvalidArgumentException $exc) {
    echo "QR generation and invalid-seed rejection passed.\n";
}
