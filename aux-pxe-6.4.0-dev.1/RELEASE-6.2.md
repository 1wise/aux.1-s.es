# AUX / PXE / TEC 6.2.0-dev.1

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

Entrega completa de fuentes y paquetes de desarrollo. La ISO 6.2 debe compilarse
en Bebe y validarse después; no se incluye una ISO compilada ni se declara estable.
Los informes de versiones anteriores no certifican este código.

## Cambios incorporados

- `aux-exec.service`, módulo `aux_exec.py`, socket `/run/aux-exec/control.sock` y
  diario `/run/aux-exec/state`. G/M y la consola física E usan el mismo componente.
- SSH efímero de la ISO en 4242, incluida la declaración SELinux. El canal web
  continúa por HTTPS/WSS 443; el backend CLI escucha solo en 127.0.0.1:8096.
- F4/F5 con `SupplementaryGroups=tty` y acceso a las TTY reales. Las API siguen
  ejecutándose como `aux-ai`, sin capacidades y sin privilegios root.
- Clave API visible por defecto para entrada manual larga. Se puede elegir O
  para entrada oculta; la clave permanece en memoria y no se añade al chat.
  La entrada visible queda visible en la terminal y su desplazamiento.
- Terminal web con xterm.js local y botón de pegado, disponible tras autorizar
  la conexión. El portapapeles requiere permiso del navegador cuando proceda.
- Alta TOTP en `totp.php`: contraseña de TEC, seed visible de 32 caracteres,
  parámetros del autenticador y confirmación con el primer código de seis cifras.
  La clave solo se activa después de confirmar; el proceso caduca en cinco minutos.
  Las cuentas existentes no pueden sustituir su factor desde esta pantalla.
- El comando administrativo `totp` exige `--replace` para rotar un factor existente;
  `totp-reset ID` permite repetir el alta desde la web tras recuperación administrativa.
- Instalador de Excalibur `install-web.py`: cuatro componentes, configuración
  explícita, pool PHP, copia idéntica del secreto CLI para TEC y pasarela habilitada.
  Conserva cuentas y el secreto del nodo si ya existen. Nunca los incluye en los ZIP.

## Paquetes

| ZIP | Contenido |
| --- | --- |
| `aux-suite-6.2.0-dev.1.zip` | Los cuatro ZIP siguientes, SHA-256, instalador y guías |
| `aux-pxe-6.2.0-dev.1.zip` | AUX/PXE, herramientas USB, OVH y fuentes de generación |
| `tec-platform-6.2.0-dev.1.zip` | Web completa, alta TOTP, administración y plantillas |
| `aux-cli-6.2.0-dev.1.zip` | Pasarela WSS/SSH y pruebas de transporte |
| `aux-assist-6.2.0-dev.1-sources.zip` | Receta Fedora 44, payload, pruebas y terminación ISO |

Instalación desde cero: `INSTALL-6.2.md`. Compilación: `iso-assist/README.md`
o README.md del ZIP ISO independiente. Agentes: `AGENT-6.2.md`.

## Aprobación y límites

Las propuestas de los agentes no se ejecutan hasta revisión root en F6/E.
Se mantienen diagnóstico acotado, texto bajo `/work/managed` y estado de chronyd;
no hay shell IA libre ni cambios automáticos de paquetes, red o discos.
La asistencia humana requiere SOLICITO, aceptación del técnico y AUTORIZO local.
El SSH web humano no permite aprobar acciones del agente en la consola física.

El portal consulta solicitudes mientras permanece abierto; esta entrega no añade
correo/push con la página cerrada. Yubico Authenticator almacena los TOTP en una
YubiKey conectada. La aplicación sola no sustituye a la llave.

La instalación no obtiene certificados, credenciales SMTP ni claves API. El correo
de confirmación necesita un MTA operativo; ver `tec/MAIL.md` o MAIL.md del ZIP TEC.
No se cambian las licencias del proyecto ni de terceros.

## Evidencia

Resultados reproducibles: `TEST-6.2.md` y `CHECKLIST-6.2.json`.
El usuario informó que la pasarela previa ya entrega solicitudes y los recursos
web responden 200; esos resultados pertenecen a 6.1, no a una instalación 6.2.
Quedan pendientes la instalación de esta entrega en Excalibur, ISO BIOS/UEFI,
TTY/SELinux dentro del Live, API reales, prueba de navegador y USB físico.
