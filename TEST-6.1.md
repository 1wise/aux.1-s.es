# Verificación AUX 6.1.0-dev.1

Timestamp: 2026-10-17 | Version: 6.1.0-dev.1
Author & Credits: https://www.alawise.es/1-s

| Prueba ejecutada | Resultado |
| --- | --- |
| verify.py | 65 pruebas superadas, con ZIP de esta versión reconstruido |
| verify-v6.py | 8 superadas |
| iso-assist/test_ai.py | 14 superadas; HTTPS/API con fixtures |
| iso-assist/test_sources.py | 11 superadas |
| iso-assist/test_executor.py | 19 superadas; 1 omitida por restricción AF_UNIX |
| verify-v61.py | 11 superadas; OVH, GPT/CRC, payload y límites |
| cli/test_cli.py | 10 superadas; SSH real local, TLS/WSS y consentimiento |
| tec/test_platform.py | PASS con PHP 8.3: cuentas, correo de prueba, aprobación, JSON y suspensión |
| verify-routing.py | PASS: URL centrales y selección de host PHP |
| verify-portal.cjs | PASS: búsqueda, filtros y enlaces con Node VM; no navegador |
| systemd-analyze verify | Unidades G/M, executor y tech-work válidas sintácticamente |
| bash -n / node --check | Scripts nuevos y CLI JS sin errores sintácticos |

Total de pruebas unitarias: 138 superadas y 1 omitida. No se utilizaron claves
API ni cuentas de clientes. Las operaciones de escritura fueron sobre archivos
temporales. Los cambios de servicio y las respuestas de proveedor usan fixtures.

La prueba inicial sobre un ZIP antiguo detectó la versión 6.0 dentro del paquete;
se reconstruyó el ZIP de 6.1 y la regresión completa pasó. La integración real
de socket Unix no puede ejecutarse en este entorno (EPERM): se conserva una
prueba que debe pasar en la ISO; NO se sustituye por un supuesto resultado verde.

No se ha compilado/arrancado la ISO 6.1 ni grabado/formateado un USB. Sin pruebas
en navegador real, API reales, SELinux, Excalibur, OVH o Kamala. No se han probado
kernel persistente ni paquetes porque esas funciones no están implementadas.
No declarar estable ni heredar como propias las pruebas de la ISO 6.0 anterior.
