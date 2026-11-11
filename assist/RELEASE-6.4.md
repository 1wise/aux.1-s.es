# AUX / WAN Arsenal / TEC 6.4.0-dev.1

Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
Author and Credits: https://www.alawise.es/1-s

## Dos terminales por caso

Abrir terminal desde CLI o desde el registro de casos abre una pestaña nueva
del navegador. Contiene Terminal 1 y Terminal 2, con su propia shell, salida,
directorio de trabajo y controles Paste y ^C / Ctrl+C. Cambiar de pestaña no
cierra las terminales. El panel de solicitudes sigue disponible por separado.

Las dos PTY comparten un transporte SSH dentro de la autorización del mismo
técnico. Los mensajes se dirigen al canal 1 o 2. Pegar conserva el destino elegido
al pulsar; una reconexión durante el permiso de portapapeles cancela ese pegado.
Ctrl+C envía el byte ETX solo a esa terminal. Finalizar una shell no finaliza la
otra. Revocar el caso o caducar el segundo factor corta ambas.

La ruta antigua `cli.php?node=...&session=...` redirige a la nueva página
`terminal.php`. Los enlaces de apertura usan `target="_blank"` y `noopener`.
No incluyen tickets, tokens ni claves. La nueva página conserva las comprobaciones
de cuenta, técnico activo, segundo factor y titularidad del caso.

## Actualizar los componentes juntos

La web y el gateway necesitan la nueva versión. El cliente Live debe anunciar
dos terminales e incluir el selector SSH revisado y las dos sesiones tmux.
La web avisa si la ISO antigua solo admite una terminal. Se mantiene el protocolo
anterior de una terminal para clientes web anteriores; las API G/M siguen
siendo agentes separados de las terminales humanas.

El ZIP contiene fuentes completas para compilar la ISO y construir la llave.
No contiene una nueva ISO ni una imagen USB combinada ya compiladas. Usar una
ISO compilada con las fuentes 6.4 para actualizar también el perfil limpio.
Las autorizaciones de USB persistente conservan su plazo inicial de ocho horas.

## Red local y WAN Arsenal

El Live crea su propia conexión Ethernet mediante NetworkManager y obtiene
DNS de la conexión. `/etc/resolv.conf` apunta al resolver que NetworkManager
regenera en `/run`. Se retiran perfiles y estado del constructor en `%post`,
sin borrar perfiles Wi-Fi al reiniciar una llave persistente.

El menú espera como máximo 15 segundos antes de abrirse. Sin conexión sigue
disponible la recuperación local y N/nmtui. Los arranques locales no exigen DHCP
en initramfs; las imágenes obtenidas por red conservan su inicialización de red.
WAN Arsenal vuelve a nombrar el menú iPXE y la entrada GRUB de red. La imagen
pequeña iPXE precompilada conserva su compilación anterior; su fuente incluye
la nueva etiqueta para la próxima reconstrucción.

## Entrega completa

| Archivo | Contenido |
| --- | --- |
| aux-pxe-6.4.0-dev.1.zip | Catálogo, generador WAN Arsenal y fuentes AUX/PXE |
| tec-platform-6.4.0-dev.1.zip | Web TEC, página de dos terminales y controles |
| aux-cli-6.4.0-dev.1.zip | Gateway con dos canales PTY, historial y pruebas |
| aux-assist-6.4.0-dev.1-sources.zip | Receta Fedora 44, red, SSH y pruebas del Live |
| aux-portable-6.4.0-dev.1-kit.zip | Constructor y payload público de la llave combinada |

La suite incluye los cinco componentes, SHA256SUMS, instalador y guías.
Se recupera el árbol de fuentes TEC a partir del paquete 6.3 incluido en Git,
y se completa la vista de la receta histórica necesaria para el empaquetado.
Los paquetes anteriores se conservan como referencia del despliegue previo.
La nueva entrega no incorpora credenciales de usuarios ni cambia licencias.

Verificación: TEST-6.4.md. Instalación: INSTALL-6.4.md.
