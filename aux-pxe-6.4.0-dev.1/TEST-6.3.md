# Verificación AUX 6.3.0-dev.2

Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
Author & Credits: https://www.alawise.es/1-s

## Verificado en dev.2

- `cli/test_history.py`: 4 pruebas de historial durable, aislamiento, paginación,
  identidad tras reiniciar, ausencia de secretos y revocación con disco de diario fallido.
- `tec/test_registry.php`: registros, repetición idempotente, notas, seguimiento,
  límites entre técnicos, cambio de cliente de una llave e historial conservado.
- `tec/test_registry_web.py`: página PHP real contra gateway TLS; sesión y TOTP,
  CSRF, etiquetas persistentes, escape HTML, denegación entre técnicos, cierre y offline.
- `tec/test_registry_ui.cjs`: DOM Node con estados, texto seguro y borradores retenidos.
- Regresión repetida: CLI 15, agente/reanudación/fuentes ISO 19, catálogo 65,
  plataforma PHP, 8 contratos v6, 11 contratos v6.1, 5 contratos v6.3, enlace terminal
  desde el panel y comprobaciones de paquete. Sin llamadas a proveedores ni correos.

No se dispone de un navegador completo en este entorno. Los flujos DOM y HTTP
no sustituyen la aceptación visual en navegador ni la prueba física de Fedora.

## Base verificada en dev.1 (evidencia conservada)

| Comprobación | Resultado |
| --- | --- |
| iso-assist/test_ai.py | 20 pruebas: entrada visible/oculta, precarga por proveedor, sustitución temporal, ausencia de secretos en salida y fixture de 165 caracteres |
| iso-assist/test_exec.py | 19 superadas y 1 omitida: AF_UNIX bloqueado en este entorno |
| iso-assist/test_sources.py | 13 pruebas de receta/payload/cancelación/arranque |
| iso-assist/test_resume.py | 5 pruebas: identidad, caducidad, reloj, permisos, clave de host estable y diferencia entre apagado y cancelación |
| iso-assist/test_resume_web.py | 1 integración: agente real por HTTPS/WSS local, permiso persistido, reconexión sin segunda autorización y cierre remoto |
| usb/portable/test_portable.py | 10 pruebas de perfiles, identidad, imagen nueva, publicación atómica de kernel y claves API privadas |
| cli/test_cli.py | 10 pruebas de transporte SSH, TLS/WSS, permisos, certificado rechazado y revocación |
| cli/test_resume.py | 5 pruebas: reinicio de gateway, plazo fijo, cierre offline y dos terminales SSH reales sucesivas en el mismo caso |
| tec/test_cli_ui.cjs | Flujo DOM Node: refresco, botón dinámico, terminal retenida, reconexión y aislamiento de un transporte anterior |
| verify-v63.py | 5 contratos de instalador, archivos, checksum y suite completa |
| verify-v61.py | 11 pruebas de materialización y guardas USB |
| verify-v6.py | 8 pruebas de regresión |
| verify.py | 65 comprobaciones de catálogo, descarga, generación y enlaces; el enlace USB 6.3 se corrigió y se repitió su comprobación |
| PHP | test_platform.py, test_cli.php, test_enroll.php y test_enroll_web.py; sintaxis de todos los archivos TEC |
| nginx/test_vhosts.py | Seis nombres, HTTP/TLS, rutas web, MIME y rutas privadas en un servidor temporal |
| Menús GRUB | Sintaxis del cargador, menú portable y publicación de kernels |
| Cargador pequeño | iPXE BIOS/UEFI recompilado; extracción de ambos binarios y grub.cfg verificada contra sus fuentes |
| QEMU BIOS y UEFI | Arranque real del cargador hasta GRUB, inspección visual de negro/verde/azul y lanzamiento inicial de iPXE sin NIC |
| Empaquetado final | CRC, SHA-256, cinco componentes, fuentes, plan de instalador y kit portable extraído |

Las pruebas usan datos y claves ficticias, certificados locales y directorios
temporales. No llaman a APIs facturables ni envían correo a personas. La prueba
HTTPS/WSS usa un agente real con arranque SSH simulado; las otras pruebas de CLI
sí conectan clientes y servidores SSH reales locales. No representan un reinicio
físico de un cliente Fedora.

El rechazo de certificado intencionado puede producir un ConnectionResetError
en el registro del servidor de prueba; la suite termina OK. El socket Unix
requiere la prueba equivalente dentro del Live con permisos reales aux-ai/aux-exec.

## Límites pendientes

No se ha compilado la ISO AUX 6.3 ni la imagen combinada. QEMU se utilizó solo
para el cargador pequeño, sin discos de cliente ni red; no prueba el Live,
persistencia de paquetes/kernel o reanudación del caso tras un reinicio real.

Pendientes: instalación real en Fedora/Excalibur, certificados públicos y SMTP;
arranque del Live BIOS/UEFI y SELinux enforcing; TTY/socket Unix reales; USB físico,
Wi-Fi/DHCP/reloj, caso web/C tras reiniciar, actualización de kernel, APIs reales
y prueba de navegador/portapapeles/YubiKey. Los contratos de código y las pruebas
simuladas no se presentan como aceptación de ese hardware.
