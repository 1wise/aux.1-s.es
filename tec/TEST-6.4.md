# Verificación AUX 6.4.0-dev.1

Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
Author and Credits: https://www.alawise.es/1-s

## Pruebas de la revisión

- `cli/test_cli.py`: transporte SSH real con dos PTY en una conexión, aislamiento
  de bytes y UTF-8, Ctrl+C dirigido, salida independiente, canal inválido,
  revocación, caducidad, clave de host y clientes anteriores.
- `tec/test_cli_ui.cjs`: listado independiente y enlaces a pestaña nueva,
  sin abrir transportes ni emitir tickets desde el sondeo del panel.
- `tec/test_terminal_ui.cjs`: dos terminales retenidas, cambios de pestaña,
  pegado dirigido y fragmentado, Ctrl+C, salida de una shell, reconexión,
  portapapeles pendiente de otra conexión, segundo factor y cierre.
- `tec/test_registry_web.py`: PHP real frente a gateway TLS local; verifica
  la nueva página, enlaces, dos controles de cada tipo, titularidad, TOTP,
  sesión anónima, CSRF y redirección desde enlaces anteriores.
- `iso-assist/test_network.py`: resolver regular, ausente o colgante; perfiles
  de construcción, preservación de destinos y entrega del módulo en Kickstart.

También se ejecutan las regresiones de receta, IA, ejecutor, reanudación, registro,
generación, instalador, sintaxis PHP y CRC/SHA-256 de los cinco paquetes.
Los casos usan cuentas ficticias y claves efímeras; no consultan proveedores API.

## Límites

Las pruebas de transporte usan un servidor SSH real local. Los procesos de shell
de ese fixture y el DOM Node se controlan para comprobar el protocolo. No son una
prueba del Live Fedora con SELinux ni de la experiencia del portapapeles en todos
los navegadores. La nueva ISO y la llave deben compilarse y arrancarse en Bebe.
Validar BIOS/UEFI, DHCP/DNS, Wi-Fi guardado y Ctrl+C sobre procesos reales del Live.

El navegador de pruebas no pudo conectar con el servidor local de la vista
aislada (`ERR_CONNECTION_REFUSED`). La revisión visual y del portapapeles en
navegador queda pendiente; no se presenta el DOM simulado como esa aceptación.

## Resultados de regresión

| Grupo | Resultado |
| --- | --- |
| Gateway, SSH, historial y reanudación | 24 pruebas correctas |
| Receta Live, red, IA, ejecutor y reanudación | 63 ejecutadas: 62 correctas y 1 omitida por el entorno |
| Constructor USB | 10 pruebas correctas |
| Catálogo, descarga, despliegue y portal | 65 pruebas correctas |
| Contratos v6 / v6.1 / v6.3 | 8 / 11 / 5 correctas |
| Entrega 6.4 | 5 pruebas: CRC, SHA-256, entradas únicas, fuentes exactas y plan del instalador extraído |
| DOM Node | Solicitudes, dos terminales y registro de casos correctos |
| PHP | Sintaxis, TOTP, registro, cuentas y páginas reales contra TLS local correctos |
