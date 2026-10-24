# AUX Suite 6.4.0-dev.1

Timestamp: 2026-10-24 | Version: 6.4.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

Esta entrega reúne los componentes de AUX/PXE, TEC, la pasarela CLI y las fuentes
del Live Fedora 44. Está preparada para revisar el despliegue en Excalibur y
compilar en Bebe la nueva ISO y la llave. La ISO y la imagen USB 6.4 todavía no
están compiladas ni probadas en hardware.

## Contenido

| Archivo | Función |
| --- | --- |
| `aux-pxe-6.4.0-dev.1.zip` | Portal AUX, catálogo, iPXE, descargas y despliegue RAM/disco/FTP |
| `tec-platform-6.4.0-dev.1.zip` | Web de técnicos y espacio de dos terminales por caso |
| `aux-cli-6.4.0-dev.1.zip` | Pasarela SSH/WebSocket con dos canales PTY |
| `aux-assist-6.4.0-dev.1-sources.zip` | Fuentes y pruebas para construir el Live Fedora 44 |
| `aux-portable-6.4.0-dev.1-kit.zip` | Constructor de la llave, con parche del Live 6.4 |

Cada componente tiene su archivo `.zip.sha256`. El `SHA256SUMS` de esta carpeta
verifica los archivos de la suite. Las carpetas extraídas son cómodas para
consultar y probar; los ZIP son las unidades que utiliza `install-web.py`.

## Primeros pasos en Excalibur

Descargar o descomprimir la suite completa en un directorio nuevo y mantener
juntos sus cinco ZIP, sus sumas, la configuración de ejemplo y el instalador.

```bash
sha256sum -c SHA256SUMS
python3 install-web.py --help
python3 install-web.py
```

El último comando solo muestra el plan. Revisar la configuración real, dominios,
certificados, rutas y servicios antes de usar `--apply`. La instalación no
reemplaza por sí sola las cuentas, claves ni datos privados existentes. La web
TEC, la pasarela CLI y el Live deben actualizarse juntos para usar las dos
terminales. Ver [INSTALL-6.4.md](INSTALL-6.4.md) para el procedimiento y
[INSTALL-6.3.md](INSTALL-6.3.md) para la preparación detallada de servicios.

## Construcción y comprobación

El Live se construye a partir del paquete `aux-assist-6.4.0-dev.1-sources.zip`.
Su propio README detalla Fedora 44, KVM, la receta y las pruebas. El kit USB
debe recibir la nueva ISO para actualizar los perfiles persistente y limpio.
La corrección de DHCP/DNS de esos perfiles y el nombre WAN Arsenal forman parte
de esta revisión.

La página CLI abre otra pestaña con Terminal 1 y Terminal 2, cada una con
Pegar y Ctrl+C. El paquete conserva los clientes de un terminal existentes,
pero para abrir dos terminales se requiere web, gateway y cliente Live 6.4.

[RELEASE-6.4.md](RELEASE-6.4.md) describe los cambios;
[TEST-6.4.md](TEST-6.4.md) distingue las pruebas automáticas ya realizadas de
la aceptación pendiente en navegador y hardware.
