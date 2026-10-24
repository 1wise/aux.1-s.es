# Instalación desde cero · Excalibur y Bebe

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

## 1. Extraer la suite en una carpeta nueva

Verificar primero el archivo SHA-256 que acompaña la suite. Extraerla y entrar
en su carpeta. No extraer directamente en la raíz pública de Nginx.

```bash
sha256sum -c aux-suite-6.2.0-dev.1.zip.sha256
mkdir aux-6.2
unzip aux-suite-6.2.0-dev.1.zip -d aux-6.2
cd aux-6.2
sha256sum -c aux-pxe-6.2.0-dev.1.zip.sha256
sha256sum -c tec-platform-6.2.0-dev.1.zip.sha256
sha256sum -c aux-cli-6.2.0-dev.1.zip.sha256
sha256sum -c aux-assist-6.2.0-dev.1-sources.zip.sha256
python3 install-web.py
```

El último comando solo muestra el plan. Se puede ejecutar también desde el
proyecto fuente completo, sin ZIP intermedios.

## 2. Excalibur: requisitos y configuración

Objetivo del instalador: Fedora, Nginx, pool dedicado PHP `tec`, nodo `excalibur`.
Un hosting compartido OVH necesita `ovh/assemble.py`; no puede alojar aux-cli.

```bash
sudo dnf install python3 python3-pip nginx php-cli php-fpm openssl \
  openssh-clients policycoreutils-python-utils postfix unzip
```

DNS debe dirigir AUX/PXE/TEC y cli.1-s.es a Excalibur. Antes de `--nginx`, disponer
de un certificado con todos los nombres que declara la plantilla: aux/pxe/tec
.1-s.es y .1-s.eu, más cli.1-s.es. La ruta predeterminada es
`/etc/letsencrypt/live/ntp1.1-s.eu/`; el nombre del directorio no certifica sus SAN.
Se puede revisar/cambiar tls.certificate y tls.key en fast-boot.json antes de instalar.
Para una ruta de certificado distinta en instalación limpia, extraer primero los
tres paquetes web en un directorio fuente (PXE en raíz, TEC en tec/, CLI en cli/)
y editar su fast-boot.json antes de ejecutar el instalador con `--source`.

En reinstalación, retirar los vhosts antiguos duplicados de AUX/PXE/TEC/CLI antes
de instalar las plantillas nuevas. Conservar una copia administrativa de esa
configuración y de `/var/lib/aux-assist`; no borrar cuentas para actualizar código.

```bash
sudo python3 install-web.py --apply --nginx
```

Sin `--nginx`, se conserva el Nginx administrado manualmente y se instala el resto.
El instalador valida PHP/Nginx antes de recargar y deja copia del código y vhosts
anteriores bajo `/var/backups/aux-assist/`. No es una transacción de todo el servidor.
Si falla una fase, revisar el error y la copia previa antes de repetirla.

El instalador realiza estas operaciones:

- Copia fuentes fuera de las raíces públicas, web TEC completa en
  `/var/www/aux.1-s.es/web` y AUX/PXE en `/var/www/aux.1-s.es/html`.
- Crea usuarios de sistema tec/aux-cli, pool tec y almacenes privados.
- Conserva `/etc/aux-cli/secret` o crea uno nuevo de 64 caracteres hexadecimales;
  instala el MISMO contenido en `/var/lib/aux-assist/cli-excalibur.secret` para PHP.
- Habilita `cli.enabled` en el JSON central. El pool incluye AUX_ASSIST_CONFIG
  explícitamente y el gateway recibe su copia privada de configuración.
- Configura etiquetas SELinux y habilita `httpd_can_network_connect` para las
  conexiones PHP/Nginx requeridas y `httpd_can_sendmail` para correo. SELinux sigue
  enforcing; estas opciones permiten red/correo a los procesos del dominio HTTP.
- Instala dependencias Python en `/opt/aux-cli/venv`, inicia aux-cli/PHP/Nginx y
  genera índices sin descargar ISO ni modificar discos de clientes.

El MTA/relay SMTP se configura aparte con MAIL.md. No se envía correo de prueba
automático. HTTPS público debe estar permitido por el cortafuegos existente;
8096 se mantiene en loopback. 4242 pertenece al cliente ISO, no a Excalibur.

## 3. Cuenta y segundo factor

1. Abrir https://tec.1-s.es/, registrar la cuenta y confirmar el correo.
2. Entrar y enviar el perfil de técnico con la clave pública SSH.
3. Como administración, listar y aprobar el identificador real del perfil:

```bash
sudo -u tec php /var/www/aux.1-s.es/manage.php list
sudo -u tec php /var/www/aux.1-s.es/manage.php approve tec_ID_REAL
```

4. Entrar en TEC → Cuenta → Configurar segundo factor (`totp.php`). Confirmar la
   contraseña, añadir la clave mostrada al autenticador y verificar un código.
   Parámetros: TOTP, SHA-1, 6 dígitos, 30 segundos. Yubico Authenticator requiere
   una YubiKey conectada; si exige contacto, calcular el código y tocar la llave.
5. La confirmación abre cli.php con autorización de 15 minutos. Después se usa un
   código nuevo; repetir el mismo código es rechazado intencionadamente.

Para recuperar un factor perdido con intervención administrativa:

```bash
sudo -u tec php /var/www/aux.1-s.es/manage.php totp-reset tec_ID_REAL
```

Después repetir el alta web. Este comando invalida el factor anterior.
No enviar seeds ni secretos por este chat ni incluirlos en ZIP o raíz pública.

## 4. Comprobación del servidor

```bash
systemctl is-active aux-cli php-fpm nginx
curl --fail http://127.0.0.1:8096/health
curl --fail https://cli.1-s.es/health
```

Health debe indicar `6.2.0-dev.1` y nodo excalibur. Entrar en cli.php, completar
el TOTP y comprobar estado conectado. Crear una nueva solicitud desde la ISO;
una petición pendiente de una versión anterior no sobrevive al reinicio de aux-cli.

Los avisos funcionan con la página abierta. Las solicitudes web de la ISO y los
formularios de contacto/instalación de TEC son flujos distintos.

## 5. Bebe: construir la ISO nueva

Extraer `aux-assist-6.2.0-dev.1-sources.zip` en un directorio nuevo. Seguir README.md
del paquete para preparar Kickstart, compilar con livemedia-creator virtual y
terminar una ISO nueva con finish.py. Nunca usar ese Kickstart en discos de clientes.
La suite contiene las fuentes completas, no una ISO ya compilada.

Tras arrancar, comprobar `aux-exec.service`, F4/F5, F6/E, puerto 4242, SELinux y
asistencia desde otra red. `aux-gpt`, `aux-gemini` y `aux-exec` van dentro de la ISO.
