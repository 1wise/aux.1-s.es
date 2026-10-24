<?php
/** Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Export only approved public profiles in the existing ISO profile format.
 */
declare(strict_types=1); define('AUX_ASSIST_ENTRY',true); require __DIR__.'/lib.php';
header('Content-Type: application/json; charset=utf-8'); header('X-Content-Type-Options: nosniff'); header('Cache-Control: no-store');
try { echo json_encode(tecnicos_publicos(), JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR); }
catch (Throwable $exc) { http_response_code(503); echo '{"error":"Perfiles no disponibles"}'; }
