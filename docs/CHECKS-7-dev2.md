# Comprobaciones de la entrega 7

Timestamp: 2026-11-09 | Version: 7.0.0-dev.2  
Author & Credits: https://www.alawise.es/1-s

Las comprobaciones siguientes se ejecutaron sobre las fuentes incluidas en esta
entrega. Los resultados de código y protocolo se distinguen de la aceptación
de una instalación real.

| Comprobación ejecutada | Resultado |
|---|---|
| Catálogo, fuentes, publicación, perfiles, planes y destinos de instalación | 29 pruebas aprobadas. |
| API, ejecutor acotado, permisos y reconexión del cliente | 46 pruebas ejecutadas: 45 aprobadas y 1 omitida por limitación del entorno. |
| Gateway: tickets, dos terminales, transporte TLS/SSH, historial, reconexión y revocación | 24 pruebas aprobadas. |
| Portal PHP: cuentas, confirmaciones, perfiles, aprobación y propiedad de datos | Aprobado; correo simulado en un buzón local. |
| Alta TOTP real: sesión, CSRF, contraseña, confirmación, redirección y restablecimiento | Aprobado. |
| Panel PHP contra gateway TLS: identidad, vistas privadas, notas escapadas, revocación e historial | Aprobado. |
| QR con qrencode real y rechazo de secreto inválido | Aprobado. |
| Sintaxis de los archivos PHP de TEC | Aprobada. |
| Compilación de módulos Python del cliente, CLI y herramientas | Aprobada. |
| Índice oficial Debian Testing y su SHA256SUMS | Lectura y publicación reales aprobadas; 1 entrada, con hash de composición. |

Total de pruebas unittest: **98 aprobadas y 1 omitida**. Las comprobaciones PHP
y de fuente oficial figuran aparte; no se convierten en un número inventado de
pruebas individuales. El índice Debian repetía un enlace desde icono y texto;
se corrigió la deduplicación y se cubrió con la prueba de regresión del adaptador.
El ejemplo JSON de esa lectura está en `DEBIAN-CATALOG-SMOKE.json`.

Entorno: Python 3.12.14, aiohttp 3.14.4, asyncssh 2.24.0, PHP 8.3.6.
Para reproducir en un entorno con las dependencias instaladas:

```bash
python3 -m unittest discover -s tests7 -v
cd assist
python3 -m unittest test_ai.py test_exec.py test_resume.py test_resume_web.py
cd ../cli
python3 -m unittest test_cli.py test_history.py test_resume.py
cd ../tec
python3 test_platform.py
python3 test_enroll_web.py
python3 test_registry_web.py
php test_totp_qr.php
```

Los scripts PHP de prueba aceptan `--php` para indicar el intérprete. La prueba
QR admite como primer argumento la ruta del ejecutable qrencode. Las claves y
cuentas de prueba son temporales; no se enviaron mensajes externos.

## Aceptación pendiente

| Recorrido | Estado |
|---|---|
| Resolución real de todos los paquetes en Debian Testing y Fedora Rawhide | Pendiente en los constructores nativos. |
| DNF installroot y debootstrap con todos los perfiles | Pendiente; comprobados los planes y archivos, no la instalación completa. |
| Construcción de aux.iso y pxe.iso | Pendiente; no se incluyen ISO nuevas. |
| Arranque de cada ISO en BIOS y UEFI | Pendiente. |
| Ejecución de los pasos de copia e instalación de AUX desde los instaladores | Pendiente en VM. |
| Instalación, cargador, initramfs genérico y arranque sin ISO | Pendiente. |
| Portabilidad y persistencia de una llave instalada en otro equipo | Pendiente. |
| Integración real del cliente con SELinux/AppArmor, XFCE y consolas | Pendiente; las pruebas de protocolo no sustituyen el arranque. |
| Montaje, desbloqueo, chroot y salida sobre un disco sintético | Pendiente en VM. |
| Firma de fuente y arranque de la imagen Debian del smoke test | No comprobados; no se descargó la ISO ni se emitió una receta PXE para ella. |
| Despliegue real de esta entrega en Excalibur | No realizado. |
| Secure Boot | No declarado; pendiente por artefacto. |

La entrega es un paquete de fuentes de desarrollo con pruebas locales. Estos
estados impiden presentarlo como una ISO instalada y aceptada.
