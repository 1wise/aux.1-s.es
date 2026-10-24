# AUX / PXE / TEC 6.3.0-dev.2

Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
Author & Credits: https://www.alawise.es/1-s

Suite de desarrollo completa. Incluye el cargador de red BIOS/UEFI recompilado,
web TEC, pasarela CLI, fuentes de la ISO Fedora 44 y constructor USB combinado.
No incluye una ISO AUX compilada ni una imagen USB combinada ya construida.
El arranque real del Live, SELinux y la aceptación con hardware siguen pendientes.

## Registro de clientes y llaves · dev.2

El panel `cases.php` añade clientes privados por técnico, inventario de USB,
casos y notas, fechas de seguimiento y filtros. El gateway conserva un diario
SQLite de eventos incluso después de cerrar o caducar el permiso. Tras AUTORIZO,
el agente persistente comunica UUID de la llave e identidad de equipo resumida;
las próximas aprobaciones se vinculan a ese inventario. Un reinicio conserva el
mismo caso. El panel actualiza conexiones cada cinco segundos y marca estado
desconocido cuando no puede verificarlo. C independiente dispone de registro
manual; no se presenta como monitorización automática. Detalles: `tec/REGISTRY.md`.

La ISO y llave combinada siguen pendientes de compilación y prueba física.
El cargador pequeño es el binario ya verificado en dev.1; no se recompiló para
este cambio del registro web. Ningún servidor público se ha actualizado aquí.

## Cambios de 6.3

- Fondo negro en GRUB e iPXE; texto normal verde y selección azul oscuro. El
  cargador pequeño se recompiló con la misma paleta; no es solo un cambio web.
- Llave combinada: primera entrada persistente, elegida por ID tras 5 segundos;
  arranque local limpio y red iPXE en el mismo menú. El firmware debe arrancar USB.
- Persisten sistema, paquetes, /work y /storage. El ayudante publica kernel e
  initramfs Live genérico y conserva una entrada anterior cuando quedan sus módulos.
- Casos de asistencia reanudables durante ocho horas desde la autorización inicial,
  ligados al mismo equipo por UUID de hardware, a la llave y al técnico autorizado.
  Reiniciar no amplía el plazo. Ctrl-C/F6 o cerrar en TEC cancela el caso.
- La pasarela guarda los casos autorizados en /var/lib/aux-cli/cases, con acceso
  privado. Una desconexión muestra reconectando; cerrar el caso elimina el permiso.
  El servidor puede reiniciarse conservando esos casos.
- El Live restaura la asistencia sin volver a pedir W/C ni AUTORIZO mientras el
  permiso siga vigente. TEC reconecta una terminal que ya estaba abierta; una
  sesión/TOTP caducada del técnico exige identificarse de nuevo.
- En un caso web, la clave pública del perfil TEC puede autorizar también SSH
  directo en 4242: la consola muestra ambas rutas antes de AUTORIZO. Se conserva
  la misma clave de host SSH del caso. Sin clave de perfil, el caso web solo abre loopback.
- C iniciada localmente también admite reinicios. Su cierre y plazo son locales;
  no se anuncia control de cierre desde TEC para un caso que no esté registrado allí.
- Precarga opcional de GPT/Gemini en AUX/private/api/openai.key y gemini.key.
  G/M permiten L para la guardada o V/O manual; K guarda, sustituye o borra.
  I cierra los asistentes y las copias de preparación en RAM, conservando los archivos.
  Son archivos root 0600 sin cifrado; no forman parte de la ISO pública.
- Se incluyen el refresco automático de solicitudes TEC, alta web TOTP, xterm.js
  local con botón de pegado, puerto 4242 y nombre aux-exec de las versiones anteriores.

Las claves API se cargan al abrir el asistente; prepararlas no realiza consultas.
Las API siguen ejecutándose como aux-ai y sus acciones requieren el flujo E de
aprobación local. No hay shell ni administración de discos ofrecida al modelo.

## Límites de reanudación

La reanudación solo corresponde al perfil USB persistente. PXE y modo limpio
mantienen autorización por arranque. El modo limpio no lee el permiso guardado.
Mover la llave a otro equipo o no disponer de una identidad de hardware estable
requiere autorización nueva. La hora del equipo debe ser correcta; un retroceso
significativo de reloj invalida el caso. La identidad DMI no es una atestación TPM.

Se recuperan los archivos y el permiso. Cada reinicio termina procesos, tmux y la
shell: se abre una terminal nueva. Un cambio DHCP requiere localizar la nueva IP
para C; el caso web se reconecta por su canal HTTPS saliente.

Un caso web verifica su existencia en CLI antes de reabrir SSH, también su ruta C.
Sin pasarela/red se conserva el caso y se reintenta con espera hasta 30 segundos.
Un caso cerrado en TEC mientras el cliente estaba apagado se rechaza al volver.

## Paquetes

| Archivo | Contenido |
| --- | --- |
| aux-pxe-6.3.0-dev.2.zip | AUX/PXE, catálogo, herramientas, fuentes y cargador de red |
| tec-platform-6.3.0-dev.2.zip | Web TEC completa, TOTP, xterm y administración |
| aux-cli-6.3.0-dev.2.zip | Pasarela, unidad systemd y pruebas de transporte/reanudación |
| aux-assist-6.3.0-dev.2-sources.zip | Receta de ISO y payload, pruebas y herramientas portables |
| aux-portable-6.3.0-dev.2-kit.zip | Constructor USB combinado con su payload público |

La suite reúne los cinco paquetes, sus SHA-256, instalador y guías. No se
incorporan secretos reales, cuentas, seeds TOTP ni credenciales API de usuarios.
No se cambian las licencias del proyecto ni de sus componentes.

Pruebas y límites: TEST-6.3.md y CHECKLIST-6.3.json. Instalación: INSTALL-6.3.md.
