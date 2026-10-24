# TEC · técnicos y asistencia

Timestamp: 2026-10-17 | Version: 6.4.0-dev.1
Author & Credits: https://www.alawise.es/1-s

Proyecto independiente de AUX/PXE. Dominio principal https://tec.1-s.es;
tec.1-s.eu sirve como alias. Los enlaces aux./, PXE_ y tec.* conectan los
servicios. La vista terminal usa ?view=pxe y funciona sin JavaScript.

## Instalación 6.3

La suite completa incorpora install-web.py e INSTALL-6.3.md para preparar TEC,
AUX/PXE y aux-cli juntos. El instalador sincroniza el secreto CLI y habilita el
portal. La cuenta activa configura su segundo factor desde totp.php, tras
confirmar la contraseña y un primer código. No es necesario generar el seed por CLI.
El comando administrativo totp requiere --replace para rotar uno existente.

## Registro de clientes, USB y casos

Desde Cuenta o CLI se abre `cases.php`, con TOTP. Cada técnico dispone de su
registro privado de clientes, llaves, casos, notas y fechas de seguimiento.
La guía de uso, actualización y copias está en [REGISTRY.md](REGISTRY.md).

## Instalación independiente

Descomprimir tec-platform-6.4.0-dev.1.zip en /var/www/aux.1-s.es/.
El paquete contiene web/, manage.php, pruebas, pool PHP-FPM, correo OVH y Nginx conjunto.
Nginx debe publicar SOLO /var/www/aux.1-s.es/web. Los comandos de administración,
pruebas y documentación quedan fuera del webroot. No ejecutar generate.sh para
publicar TEC: ese comando pertenece al proyecto AUX/PXE.

Para un 502, seguir TROUBLESHOOTING.md antes de cambiar permisos: comparar el pool
cargado y fastcgi_pass, comprobar tec.sock y leer tec.error.log/journal. La nueva
plantilla conserva la ruta de socket y añade PATH explícito y catch_workers_output
para facilitar el diagnóstico. Esta actualización no altera los JSON privados.

Requisitos: PHP 8.1+, PHP-FPM, sesiones, proc_open, ssh-keygen, HTTPS y MTA local
compatible con sendmail. El proceso PHP no necesita root. Los técnicos confirman
su correo y después requieren aprobación CLI. Los clientes confirman cada
solicitud antes de que aparezca al técnico. El teléfono profesional es público
con consentimiento; el correo y teléfono del cliente son privados. No hay SMS.

Usar un pool dedicado con usuario `tec` (independiente del pool www). Preparar:

```bash
sudo useradd --system --home-dir /var/lib/aux-assist --no-create-home --shell /sbin/nologin tec
sudo install -d -m 0755 /var/www/aux.1-s.es/isos /var/www/aux.1-s.es/html /var/www/aux.1-s.es/web
sudo install -d -m 0700 -o tec -g tec /var/lib/aux-assist /var/lib/php/tec-session
sudo chown -R tec:tec /var/lib/aux-assist
sudo find /var/www/aux.1-s.es/web -type d -exec chmod 0755 {} +
sudo find /var/www/aux.1-s.es/web -type f -exec chmod 0644 {} +
sudo semanage fcontext -a -t httpd_sys_rw_content_t '/var/lib/aux-assist(/.*)?'
sudo semanage fcontext -a -t httpd_var_run_t '/var/lib/php/tec-session(/.*)?'
sudo restorecon -Rv /var/lib/aux-assist
sudo restorecon -Rv /var/lib/php/tec-session
sudo restorecon -Rv /var/www/aux.1-s.es
sudo -u tec php /var/www/aux.1-s.es/manage.php init
sudo install -m 0644 php-fpm.conf.example /etc/php-fpm.d/tec.conf
sudo touch /var/log/php-fpm/tec-error.log
sudo chown tec:tec /var/log/php-fpm/tec-error.log
sudo chmod 0640 /var/log/php-fpm/tec-error.log
sudo restorecon -v /var/log/php-fpm/tec-error.log
sudo php-fpm -t
sudo systemctl restart php-fpm
```

Si existe la regla SELinux, usar semanage fcontext -m. El nombre histórico
/var/lib/aux-assist se conserva para reutilizar los datos; no está bajo el
webroot de AUX ni TEC. Los JSON son 0600 y el directorio es 0700. Se usa flock y
reemplazo atómico. No copiar los JSON a Git, al ZIP, a Bastion ni por FTP.
AUX_ASSIST_DATA_DIR permite otra ubicación privada mediante el entorno del pool.

## DNS, TLS y correo

Crear los registros DNS de tec.1-s.es y tec.1-s.eu apuntando a Excalibur.
`nginx.conf.example` reúne AUX, PXE y TEC; sustituir los vhosts anteriores que
definan esos nombres. Usa www.sock para AUX y tec.sock para TEC. Disponer de un certificado
que cubra los seis nombres aux/pxe/tec de .es y .eu antes de activar TLS. El ejemplo es una plantilla,
no un instalador de Nginx ni Certbot. Probar nginx -t antes de recargar.

En el pool PHP-FPM:

```ini
env[AUX_ASSIST_MAIL_FROM] = tec@1wise.es
env[AUX_ASSIST_PUBLIC_URL] = https://tec.1-s.es
```

`php-fpm.conf.example` ya contiene estas variables. Configurar Postfix con la
cuenta OVH siguiendo `MAIL.md` y `postfix.conf.example`. Conservar los nombres
AUX_ASSIST_* por compatibilidad. Probar la salida del MTA
local y reiniciar php-fpm al actualizar sus variables. Si SELinux registra un
AVC que bloquea el envío, revisar el bloqueo y habilitar httpd_can_sendmail.
Los enlaces caducan a las 24 horas; solo el hash se almacena. La confirmación
requiere un botón POST compatible con Links. Reenviar invalida el enlace anterior.
La aceptación de mail() indica entrega al MTA, no garantiza llegada al buzón.

## Administración

Desde /var/www/aux.1-s.es/:

```bash
sudo -u tec php manage.php list
sudo -u tec php manage.php approve tec_ID
sudo -u tec php manage.php suspend tec_ID
sudo -u tec php manage.php requests
sudo -u tec php manage.php password tec_ID
sudo -u tec env AUX_ASSIST_MAIL_FROM=tec@1wise.es AUX_ASSIST_PUBLIC_URL=https://tec.1-s.es php manage.php resend tec_ID
```

resend también admite sol_ID. La contraseña se solicita oculta. Aprobar requiere
correo confirmado y revisión del contacto/autorización del técnico. No hay
recuperación automática de contraseña. Aceptar una solicitud no abre SSH/VPN.
El export público de perfiles queda en https://tec.1-s.es/profiles.php.

## Migración desde TECH o /assist/

Respaldar /var/lib/aux-assist y la web anterior antes del cambio. Reutilizar esos mismos JSON; no
inicializar un directorio nuevo sobre la copia. Cambiar AUX_ASSIST_PUBLIC_URL a
https://tec.1-s.es y reenviar los enlaces todavía pendientes. La cookie ahora
se llama tec_assist y usa la raíz: las cuentas requieren entrar de nuevo.

El Nginx conjunto ya incluye los redirects desde /assist/. Tras comprobar TEC,
retirar el vhost TECH anterior. Los enlaces de verificación pendientes deben
reenviarse para que utilicen el dominio TEC. Para instalaciones anteriores, los redirects son:

```nginx
location = /assist/index.php {
    return 308 https://tec.1-s.es/index.php$is_args$args;
}
location = /assist/profiles.php {
    return 308 https://tec.1-s.es/profiles.php$is_args$args;
}
location /assist/ {
    return 308 https://tec.1-s.es/;
}
```

Estos redirects evitan servir la copia PHP antigua. Su retirada física puede
hacerse tras comprobar la migración; el generador conserva archivos ajenos y no
borra automáticamente el directorio anterior. Los perfiles de pruebas anteriores
sin email_confirmado no se consideran verificados y requieren un alta nueva.

## Comprobaciones y alcance

```bash
python3 test_platform.py --php /usr/bin/php
```

Pruebas con JSON temporal y sendmail simulado; no envían correos reales. La
publicación Sites distribuye los proyectos pero no ejecuta PHP. La entrega
real del correo y DNS/TLS necesitan verificarse en Excalibur. La nueva ISO ligera,
notificaciones al técnico e integración SSH/WireGuard siguen pendientes.

## 5.1.0

Cuenta única, perfiles completos y contacto al administrador. Leer MIGRATION-5.1.0.md antes de instalar. Configuración canónica en fast-boot.json; env AUX_ASSIST_CONFIG selecciona su ruta.
