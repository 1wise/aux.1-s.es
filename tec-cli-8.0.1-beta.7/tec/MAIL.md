# Correo TEC con OVH

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

La plataforma utiliza `tec@1wise.es`. Configurar esa cuenta en Postfix; PHP
entrega el mensaje al MTA local. La cuenta anterior no se utiliza en el pool
nuevo. Esta configuración corresponde a **OVH MX Plan Europa**; si la cuenta
es Email Pro o Exchange, usar el servidor indicado por OVH para esa cuenta.
Fuente oficial:
https://github.com/ovh/ovhcloud-docs/blob/develop/docs/en/guides/web-cloud/web-hosting/email-sending-best-practices.mdx

En Fedora, instalar soporte SASL y respaldar la configuración:

```bash
sudo dnf install postfix cyrus-sasl-plain mailx
sudo cp -a /etc/postfix/main.cf /etc/postfix/main.cf.pre-tec
```

Incorporar los parámetros de `postfix.conf.example` a `/etc/postfix/main.cf`.
SMTP autenticado en `smtp.mail.ovh.net:587` con STARTTLS y certificado verificado.
No sustituir todo el archivo ni guardar contraseñas dentro del proyecto.

Crear el archivo privado si no existe y editarlo en el servidor:

```bash
sudo touch /etc/postfix/sasl_passwd
sudo chmod 0600 /etc/postfix/sasl_passwd
sudoedit /etc/postfix/sasl_passwd
```

La entrada para el relay TEC será:

```text
[smtp.mail.ovh.net]:587 tec@1wise.es:CONTRASEÑA_REAL_DE_OVH
```

Sustituir el marcador en el editor. Reemplazar el relay anterior y sus entradas
SASL; revisar también cualquier `smtp_generic_maps` o `sender_canonical_maps`
anterior que fuerce otro remitente. No borrar un buzón remoto desde esta receta.

```bash
sudo postmap /etc/postfix/sasl_passwd
sudo chmod 0600 /etc/postfix/sasl_passwd /etc/postfix/sasl_passwd.db
sudo restorecon -v /etc/postfix/sasl_passwd /etc/postfix/sasl_passwd.db
sudo postfix check
sudo systemctl restart postfix
sudo php-fpm -t
sudo systemctl restart php-fpm
```

El pool `tec.conf` declara remitente, URL pública y envelope sender. Para
administración CLI usar las mismas variables, porque la CLI no hereda el pool:

```bash
sudo -u tec env AUX_ASSIST_MAIL_FROM=tec@1wise.es \
  AUX_ASSIST_PUBLIC_URL=https://tec.1-s.es php /var/www/aux.1-s.es/manage.php resend tec_ID
```

Primero probar contra una dirección propia con sendmail o mutt usando
`tec@1wise.es` como From y envelope sender. Después probar una confirmación
desde el formulario TEC, comprobar la URL `https://tec.1-s.es/` y confirmar con
el botón POST. Consultar `sudo postqueue -p` y `sudo journalctl -u postfix`
si queda en cola. `mail()` aceptado solo confirma entrega al MTA local.
Comprobar SPF/DKIM de `1wise.es` en OVH si el destinatario rechaza el mensaje.

Si hay un AVC de SELinux por sendmail, revisar con `sudo ausearch -m AVC -ts recent`
y habilitar `sudo setsebool -P httpd_can_sendmail on` cuando corresponda.
