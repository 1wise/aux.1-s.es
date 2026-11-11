# Cockpit, SSH, tmux y AUX Assist

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Servicios instalados y acceso local

Las listas de paquetes incluyen Cockpit, servidor y cliente OpenSSH, tmux,
NetworkManager y herramientas de terminal. Comprobar qué módulos de Cockpit
existen en cada distribución. Activar Cockpit cuando se vaya a utilizar:

```bash
sudo systemctl enable --now cockpit.socket
```

Se accede habitualmente por HTTPS en el puerto 9090 con una cuenta del sistema.
Cockpit instalado localmente utiliza su autenticación/PAM. Una clave pública SSH
en `authorized_keys` no se convierte automáticamente en una credencial del login
web de Cockpit. La integración con TEC deberá respetar esa diferencia.

Para SSH administrativo estándar, los nombres habituales de unidad son `sshd`
en Fedora y `ssh` en Debian. Configurar primero la cuenta y la clave pública del
destinatario. Abrir solamente el servicio elegido y mantener la comprobación de
huella del servidor. No cambiar automáticamente todo el acceso root del equipo
para habilitar una sesión de soporte.

Instalar el paquete de servidor SSH puede habilitarlo según la distribución.
Comprobar su estado y los sockets después de instalar. Si no se va a utilizar
todavía, detener y deshabilitar la unidad correspondiente antes de publicar la
imagen. Mantener separado ese acceso administrativo del permiso de cada caso
de asistencia.

La pasarela TEC 6.4 utiliza su listener específico de asistencia, normalmente
en 4242, con clave efímera y selección de terminales. Es una vía distinta del
sshd administrativo del sistema. Sus opciones `ForceCommand` y
`DisableForwarding` no deben relajarse para improvisar un túnel a Cockpit.

Conservar una terminal local accesible aunque fallen Internet, DNS, la web o el
bus de servicios. No condicionar la apertura de XFCE o la terminal a una prueba
exitosa de `nmcli` ni iniciar un bucle de reinicio infinito del menú.

## Desplazamiento de tmux

Copiar la configuración incluida a una cuenta que vaya a abrir sesiones nuevas:

```bash
install -m 0600 config/tmux.conf "$HOME/.tmux.conf"
```

Esa ruta afecta a esa cuenta y no al servidor de asistencia que use `-S` y `-f`.
Para el servidor ya abierto de AUX Assist, aplicar los mismos ajustes:

```bash
sudo tmux -S /run/aux-assist/tmux.sock set-option -g mouse on
sudo tmux -S /run/aux-assist/tmux.sock set-option -g history-limit 20000
sudo tmux -S /run/aux-assist/tmux.sock bind-key -n S-PPage copy-mode -eu
sudo tmux -S /run/aux-assist/tmux.sock bind-key -n S-NPage copy-mode -ed
```

El socket debe existir y pertenecer a la sesión esperada. El límite se utiliza
para paneles nuevos: cambiarlo no recupera líneas que ya se descartaron ni
asegura que paneles existentes hayan aumentado su capacidad.

Para navegación de teclado siempre queda el modo copia: pulsar `Ctrl+B`, soltar,
pulsar `[` y usar RePág/AvPág. Salir con `q` o Escape según las teclas del modo.
Shift+RePág puede ser consumido por el emulador del navegador; el enlace de tmux
solo funciona si la secuencia llega a él. No anunciar ese atajo como comprobado.
Con ratón activo, seleccionar texto en el navegador puede requerir mantener
Shift pulsado, según el terminal.

El historial del panel vive en tmux. La barra de xterm solo conoce su propio
buffer. Para que una barra web recorra el historial remoto hará falta integración
de interfaz; aumentar `scrollback` en xterm por sí solo no conecta ambos.

En la migración, el generador de configuración del listener directo y cualquier
generador del agente web deben usar esta misma configuración. No basta editar
un archivo `/run` si un proceso vuelve a escribirlo durante la autorización.

Se incluye `patches/6.4-tmux-scroll.patch` para las fuentes originales 6.4. Es
una corrección acotada de scroll, no el port completo a una instalación normal.
Después de extraer las fuentes como indica la guía 09:

```bash
cd work/reference64/assist-source
patch --dry-run -p1 < ../../../patches/6.4-tmux-scroll.patch
patch -p1 < ../../../patches/6.4-tmux-scroll.patch
install -m 0644 ../../../config/tmux.conf payload/tmux.conf
```

La prueba en seco debe coincidir sin conflictos. Al empaquetar el cliente
adaptado, instalar también ese archivo junto a `assist.py`; el parche permite
que el agente web lo utilice cuando abre las terminales sin recibir otra
configuración explícita. El listener directo genera sus ajustes equivalentes.

## Portar AUX Assist existente

La referencia 6.4 contiene las fuentes existentes para SSH directo, solicitudes
web, dos terminales y agentes Gemini/GPT. **No está validada como paquete instalado
en Fedora de desarrollo y Debian Testing.** Consultar el mapa de migración de
la guía 09 antes de copiar unidades de servicio.

En particular, no activar las antiguas unidades `tech-work.service` ni las rutas
de montaje Live para dar persistencia a una instalación normal. `/work` y
`/storage` serán directorios o montajes normales explícitos. La condición de
kernel `aux.assist`, el cambio de TTY y los observadores tty7/tty8 requieren
adaptación para convivir con XFCE; esos terminales pueden estar ocupados por
la sesión gráfica.

La instalación de AUX Assist deberá tener un lanzador desde XFCE y terminal,
un servicio privilegiado limitado a las operaciones que lo necesiten y un
control local para revocar la intervención. El código y las unidades nuevos
todavía deben implementarse y probarse. No instalar todo el payload antiguo
con `systemctl enable '*.service'` como sustituto de esa adaptación.

## GPT, Gemini y TOTP

Los agentes API heredados requieren revisar modelos, endpoints, dependencias,
control de gasto y consentimiento para los datos enviados. Las claves se
configuran por la persona responsable y no se incrustan en ISO, imágenes de disco,
JavaScript ni registros públicos. Debe quedar visible qué sistema está siendo
intervenido antes de ejecutar un plan.

El portal TEC ya tenía alta TOTP; la mejora del QR debe añadirse al mismo flujo.
El QR contiene el secreto de inscripción. Se genera localmente en la plataforma
de alta, se confirma con un código y no se manda a un servicio público de QR.
La cuenta del técnico y el reloj deben estar preparados antes de exigir códigos.
El alta no se impone al cliente para abrir una petición de ayuda.

## Entrada guiada en una instalación

La aplicación deberá mostrar distribución, disco, raíz y modo de acceso;
gestionar LUKS/LVM/Btrfs cuando se admitan y conservar una lista de los montajes
que haya creado para retirarlos en orden inverso. No se incluyen comandos de
formateo ni reparación automática como parte de la detección.

En inspección, una simple opción `mount -o ro` no es una garantía forense
universal: algunos sistemas pueden reproducir su journal. Una adquisición
forense requiere una política específica del formato y, cuando corresponda,
bloqueador de escritura. La entrada chroot de reparación tendrá escritura
explícitamente autorizada y una raíz de destino identificada.

Un chroot utiliza el kernel del entorno de rescate y el espacio de usuario de
la instalación seleccionada. Debe comprobarse arquitectura y compatibilidad;
incluso entre Fedora y Debian puede funcionar, sin prometer cualquier versión
o equipo. El paquete de esta edición documenta el flujo, no lo automatiza aún.

