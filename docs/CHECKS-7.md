# Comprobaciones de 7.0.0-beta.0

Timestamp: 2026-11-10 | Version: 7.0.0-beta.0  
Author & Credits: https://www.alawise.es/1-s

| Comprobación de esta beta | Resultado |
|---|---|
| python3 -m unittest discover -s tests7 -q | 82 pruebas aprobadas. |
| Consolas reales 120x30, xterm-256color | Catalog, Setup, Profile, Images, Live Recipe y USB Image: identidad, fondo y cancelación comprobados. |
| Pruebas de consola compartida | Casillas, panel derecho, grupos, campos, temas, restauración del contexto y cancelación antes de aplicar. |
| Catálogo | Presets, límites, tamaños desconocidos, exportación y selección entre paneles/grupos. |
| Instalador | Destino explícito, sistema actual al final, aux-assist opcional, instalación repetible en raíz temporal y conservación de configuración. |
| Generador Live | Receta y fuentes generadas en directorio temporal; no se compiló una ISO. |
| Generador USB | Plan comprobado con archivo sintético y SHA-256; no se creó imagen ni se escribió un dispositivo. |
| Web local | Construcción con versión beta, 288 entradas, 186 menús externos y aplicaciones integradas. |
| Paquetes completos | ZIP y TAR.GZ extraídos; manifiestos SHA-256 comprobados. |
| node tec/test_terminal_ui.cjs | Aprobado: terminales retenidas, aislamiento, UTF-8, pegado, Ctrl+C, reconexión y estados de autorización en fixture Node. |
| node tec/test_cli_ui.cjs | Aprobado: sondeo de solicitudes y enlaces iniciados por el usuario. |
| node tec/test_registry_ui.cjs | Aprobado: estados y borradores de notas en fixture Node. |

El registro docs/terminal-beta-results.json detalla las seis pruebas PTY de esta
beta. Las pruebas Python incluyen planes y raíces temporales; no ejecutan una
instalación real del sistema anfitrión.

No repetido en este entorno: prueba DOM jsdom del instalador (dependencia no
disponible), PHP/API de TEC (PHP no disponible), pruebas SSH del gateway
(asyncssh no disponible), rastreo real actualizado de fuentes externas y revisión
visual completa del navegador. Las instantáneas de software y catálogo conservan
su procedencia previa; no se presentan como una nueva consulta de esta beta.

Pendientes: instalación Fedora/Debian, BIOS/UEFI, Secure Boot, LUKS/chroot en VM,
resolución completa de paquetes, temporizador en Excalibur, integración de páginas
de redirección, despliegue y publicación remota. No se ha construido una ISO beta.
