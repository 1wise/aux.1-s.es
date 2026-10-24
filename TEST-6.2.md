# Verificación AUX 6.2.0-dev.1

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

## Ejecutado localmente

| Comprobación | Resultado |
| --- | --- |
| iso-assist/test_exec.py | 19 superadas; 1 omitida: AF_UNIX bloqueado por el entorno |
| iso-assist/test_ai.py | 15 superadas; clave visible/oculta y fixture de 165 caracteres |
| iso-assist/test_sources.py | 13 superadas; receta/payload/cancelación/arranque |
| verify-v62.py | 5 superadas; paquetes extraídos, configuración, secreto real temporal, checksum/rutas |
| verify-v61.py | 11 superadas; regresión de materialización/USB/payload adaptada al nombre nuevo |
| verify-v6.py | 8 superadas |
| verify.py | 65 superadas, incluida la verificación de enlaces estáticos |
| cli/test_cli.py | 10 superadas; SSH y HTTPS/WSS locales, TLS rechazado, revocación y entrada larga |
| tec/test_platform.py | Superada; cuentas, correo simulado, perfiles, solicitudes y suspensión |
| tec/test_cli.php | Superada; vector RFC TOTP, repetición, caducidad y rotación |
| tec/test_enroll.php | Superada; contraseña, identidad, caducidad, alta y secreto privado |
| tec/test_enroll_web.py | Superada; página PHP real, sesión, CSRF, alta, código y redirección |
| nginx/test_vhosts.py | Superada con binario local; seis nombres, HTTP/TLS y rutas privadas |
| PHP lint | Sin errores en los nueve archivos PHP de TEC |
| cli.js | Sintaxis JavaScript correcta |

PHP 8.3.6 y Nginx 1.24 locales se usan como herramientas de prueba; no demuestran
la configuración de Fedora/Excalibur. El flujo HTTP de alta TOTP simula los
metadatos HTTPS entregados por Nginx y usa cuentas/clave de prueba temporales.
No se ha usado una cuenta real, YubiKey ni clave API.

La integración CLI produce un cierre de conexión durante la prueba intencionada
de rechazo de certificado; la suite termina OK. El socket Unix requiere la
prueba equivalente dentro de la ISO con permisos reales aux-ai/aux-exec.

Se detectó y corrigió un enlace de la guía USB 6.2 durante la regresión del
catálogo. Los resultados de empaquetado finales se registran en CHECKLIST-6.2.json.

## Pendiente

Instalar realmente install-web.py en Fedora; correo/SMTP y certificados públicos;
compilar ISO nueva y probar BIOS/UEFI, TTY, SELinux y socket Unix; API reales y
aprobación física; navegador/portapapeles/YubiKey; GSM externo; USB físico.
Los controles del instalador se prueban con archivos temporales y modo plan;
no se ejecutó --apply sobre un servidor. No se escribe ningún dispositivo físico.
