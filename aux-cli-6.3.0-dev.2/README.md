# AUX CLI 6.2.0-dev.1
Timestamp: 2026-10-16 · Author & Credits: https://www.alawise.es/1-s

6.2 mantiene el protocolo CLI de SSH humano. Las unidades aux-gpt, aux-gemini y
aux-exec pertenecen a la ISO; no se instalan aquí. No hay proxy de API IA.
Comprobación read-only desde este ZIP extraído: `bash preflight.sh`. Las órdenes
de instalación siguientes usan las rutas del proyecto completo (carpeta cli/);
en este ZIP independiente, server.py y aux-cli.service están en la raíz extraída.
Conservar secretos existentes si TEC ya está conectado. Ver RELEASE-6.2.md.

Pasarela experimental: WSS saliente del cliente → SSH privado en loopback → terminal web TEC.
Se ha probado el transporte con SSH real y fixtures locales. Esto no sustituye una prueba desde
otra red ni una revisión de seguridad antes de ofrecer acceso root a clientes reales.

## Instalación de la suite 6.2

La vía recomendada para empezar desde cero es install-web.py e INSTALL-6.2.md
de la suite: instala el backend y TEC, conserva/genera el secreto y sincroniza
su copia para PHP. El alta TOTP se realiza desde totp.php en la cuenta activa.
Las instrucciones manuales siguientes siguen disponibles para administrar cada componente.

## 1. Servicio en Excalibur

Desde el paquete completo, como administrador:

```bash
sudo useradd --system --home-dir /opt/aux-cli --shell /usr/sbin/nologin aux-cli
sudo install -d -m 0755 /opt/aux-cli
sudo install -m 0644 cli/server.py cli/history.py cli/requirements.txt /opt/aux-cli/
sudo python3 -m venv /opt/aux-cli/venv
sudo /opt/aux-cli/venv/bin/pip install -r /opt/aux-cli/requirements.txt
sudo install -d -o root -g aux-cli -m 0750 /etc/aux-cli
sudo install -o root -g aux-cli -m 0640 fast-boot.json /etc/aux-cli/fast-boot.json
sudo touch /etc/aux-cli/secret
sudo chown aux-cli:aux-cli /etc/aux-cli/secret
sudo chmod 0600 /etc/aux-cli/secret
if ! sudo test -s /etc/aux-cli/secret; then
  sudo sh -c 'openssl rand -hex 32 > /etc/aux-cli/secret'
fi
sudo install -m 0644 cli/aux-cli.service /etc/systemd/system/aux-cli.service
```

El secreto aleatorio se usa solo entre TEC y este cli. Copiar el MISMO contenido por un canal
administrativo seguro al archivo privado `cli.nodes.excalibur.secret_file` en el servidor TEC,
con permisos 0600 y propietario del pool TEC. No subirlo a Git, al FTP público ni a la ISO.
Kamala debe tener un secreto diferente, AUX_CLI_NODE=kamala y su propio endpoint TLS.

`fast-boot.json` es la fuente de configuración. AUX_CLI_CONFIG selecciona su copia instalada;
AUX_CLI_NODE selecciona el nodo y AUX_CLI_SECRET_FILE selecciona el secreto privado local.
El proceso escucha solo en 127.0.0.1:8096. La plantilla Nginx publica HTTPS/WSS en 443.

## 2. DNS, TLS, Nginx y SELinux

Preparar cli.1-s.es para Excalibur y cli-kamala.1-s.es para Kamala.
La plantilla conserva la ruta de certificado `live/ntp1.1-s.eu`, pero ese certificado debe
incluir el nombre del cli en sus SAN. La ruta o su nombre no demuestran cobertura:

```bash
sudo openssl x509 -in /etc/letsencrypt/live/ntp1.1-s.eu/fullchain.pem -noout -checkhost cli.1-s.es
```

Si no está cubierto, obtener un certificado válido para ese nombre y configurar sus rutas.
Integrar `cli/nginx.conf.example` en el contexto correcto: limit_req_zone va en `http`.
Comprobar `sudo nginx -t` antes de recargar. Abrir únicamente HTTPS público para la pasarela;
no publicar 8096. El puerto 4242 pertenece al sshd efímero del cliente ISO, no al gateway.
En Kamala, el acceso público debe funcionar sin depender del túnel de Excalibur; probarlo
desde fuera de la intranet.

Con SELinux Enforcing, examinar los AVC reales antes de ajustar la política. Nginx necesita
conectar al backend y PHP-FPM a los clis HTTPS; no desactivar SELinux para resolverlo.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aux-cli
curl --fail http://127.0.0.1:8096/health
sudo journalctl -u aux-cli -n 30
```

## 3. TEC

Instalar `tec/web` en la raíz pública TEC/T, conservando JSON, secretos y `manage.php` fuera.
El ZIP TEC incluye xterm.js 6.0.0 y su licencia; no carga JavaScript desde un CDN.
Activar `cli.enabled` en fast-boot.json solo después de disponer de DNS/TLS/servicio.
Si la configuración viaja al pool con AUX_ASSIST_CONFIG, conservar ese nombre.

Confirmar y aprobar la cuenta de técnico mediante el procedimiento existente.
La cuenta activa abre totp.php desde TEC, confirma la contraseña y añade el seed
mostrado al autenticador (TOTP, SHA-1, 6 dígitos, 30 segundos). Un primer código
válido activa el factor y abre la terminal. Yubico Authenticator requiere YubiKey.
Las cuentas con factor existente no pueden reemplazarlo desde esa pantalla.
La administración puede restablecerlo con manage.php totp-reset tec_ID.
Para un alta por CLI se mantiene manage.php totp tec_ID; la rotación exige --replace.

El código no se puede reutilizar; la confirmación dura 15 minutos. Las terminales renuevan
su autorización cada 40 segundos y se cierran si el técnico se suspende, sale o pierde el segundo factor.
La retirada por el portal queda acotada a un máximo de 75 segundos; el cierre desde la ISO es inmediato
cuando llega al proceso local. La caída del transporte también termina SSH.

El panel consulta presencia/solicitudes cada cinco segundos mientras está visible. Los avisos
de escritorio requieren permiso explícito del navegador. No hay entrega push con la web cerrada
ni envío automático de correos por la pasarela de esta versión.

## 4. Cliente

La ISO fija 5.0.1 no cambia. La receta nueva está en `iso-assist`; aún se debe compilar.
W abre el modo web. SOLICITO permite crear la solicitud saliente, sin abrir SSH.
Tras aceptar el técnico, el cliente verifica identidad/contacto/huella y escribe AUTORIZO.
Solo entonces el daemon SSH escucha en 127.0.0.1:4242 y se comunica por WSS.
Ctrl-C en F6, cierre del navegador, caducidad o pérdida de túnel cierran la asistencia.
F7/F8 son visores; T permite intervención física local. No se bloquea el teclado.

Solicitud pendiente: 10 minutos. Sesión autorizada: hasta 60 minutos. Una terminal a la vez.
Al cerrar la terminal no se reconecta automáticamente: se requiere nueva solicitud/consentimiento.
La memoria del cli contiene claves efímeras; reiniciar el servicio destruye sus sesiones.
No se graban pulsaciones ni contenido de terminal. Los logs incluyen código, técnico y cierres.
Los tokens no se transportan en URLs. El código AUX visible nunca funciona como credencial.

## 5. Verificación

```bash
python3 -m venv /tmp/aux-cli-test
/tmp/aux-cli-test/bin/pip install -r cli/requirements.txt
/tmp/aux-cli-test/bin/python cli/test_cli.py -v
```

Pruebas: consentimiento, reclamación exclusiva, técnico ajeno, Origin, tokens inválidos/repetidos,
caducidad, SSH real, bytes UTF-8 y revocación. El gateway fija la clave de host del agente,
deshabilita el uso de SSH agent local y no abre puertos TCP de forwarding.
El navegador aplica control de flujo por confirmación de bytes renderizados.

Antes de declarar estable: compilar la ISO, BIOS/UEFI, SELinux, solicitud exterior tras NAT,
Wi-Fi/latencia, cierre físico, suspensión, corte WAN y reinicio de cada cli. El traslado a Kamala
es manual; no promete migración de sesiones ni replicas JSON con escrituras simultáneas.

Fuentes técnicas: https://docs.aiohttp.org/en/stable/web_reference.html,
https://asyncssh.readthedocs.io/en/stable/api.html y https://xtermjs.org/docs/.

## Registro TEC 6.3 dev.2

`history.py` conserva eventos privados en `/var/lib/aux-cli/history.sqlite3`.
`GET /api/history?cursor=0` requiere ticket control y devuelve como máximo 200
eventos del técnico autenticado; `more` permite continuar sin perder entradas.
No devuelve tokens, claves privadas ni contenido de terminal. Cerrar un caso
elimina su permiso de reconexión, conservando el diario. El panel TEC sincroniza
ese diario con sus registros de clientes y llaves; ver `tec/REGISTRY.md` en la suite.
La plantilla Nginx limita nuevas solicitudes POST y permite el sondeo GET normal.
