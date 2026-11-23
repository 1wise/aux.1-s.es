# TEC: diagnóstico de 502 Bad Gateway

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

El Nginx conjunto envía TEC a `/run/php-fpm/tec.sock`. El pool `[tec]` debe
escuchar en esa misma ruta; el pool www de AUX es independiente. El 502 requiere
el mensaje del registro para distinguir una conexión inexistente, denegada,
rechazada o cerrada. La publicación de código no reinicia los servicios de Excalibur.

## 1. Leer el fallo y comprobar el servicio

```bash
sudo tail -n 50 /var/log/nginx/tec.error.log
sudo systemctl status php-fpm --no-pager -l
sudo journalctl -u php-fpm -n 80 --no-pager
sudo php-fpm -t
```

No publicar registros con credenciales, tokens de confirmación o datos de clientes.
Si php-fpm -t falla, corregir primero ese error: usuario tec inexistente, chdir
ausente, una directiva inválida o dos pools que usan el mismo socket pueden impedir
el inicio. Comprobar también los logs globales si tec.error.log está vacío.

## 2. Comparar el pool cargado y el upstream

```bash
getent passwd tec
getent group tec
sudo test -d /var/www/aux.1-s.es/web
sudo rg -n '^\[tec\]|^user|^group|^listen|^chdir' /etc/php-fpm.d/tec.conf
sudo ls -ldZ /run/php-fpm
sudo ls -lZ /run/php-fpm/tec.sock
sudo ss -xlpn
sudo nginx -T
```

Buscar el bloque server_name tec.1-s.es tec.1-s.eu y su fastcgi_pass. La ruta
debe coincidir con listen en el pool instalado, no únicamente con el ejemplo
del ZIP. Si rg no está instalado, usar grep -nE con el mismo patrón. /var/run
suele enlazar a /run; usar /run de forma consistente en estas dos configuraciones.

| Registro de Nginx | Comprobación | Reparación dirigida |
| --- | --- | --- |
| No such file or directory | ¿Existe tec.sock y está cargado el pool? | Instalar el pool, crear su usuario/directorios y arrancar FPM tras validar |
| Permission denied | Propietario, modo, ACL, recorrido del directorio y AVC | Ajustar acceso en la configuración del pool; revisar SELinux antes de cambiar políticas |
| Connection refused | Socket presente pero sin proceso escuchando | Revisar el servicio y reiniciar FPM después de corregir su configuración |
| upstream prematurely closed connection | Journal FPM, error PHP, crash o memoria | Corregir la causa indicada; no ocultarla aumentando timeouts |

## 3. Instalar el pool si todavía no existe

Estas operaciones son para un despliegue nuevo o incompleto. Conservar el pool y
los JSON actuales antes de sustituir una configuración. Crear el usuario tec solo
si getent confirma que falta. Desde el paquete TEC descomprimido:

```bash
sudo useradd --system --home-dir /var/lib/aux-assist --no-create-home --shell /sbin/nologin tec
sudo install -d -m 0755 /var/www/aux.1-s.es/web
sudo install -d -m 0700 -o tec -g tec /var/lib/aux-assist /var/lib/php/tec-session
sudo install -m 0644 php-fpm.conf.example /etc/php-fpm.d/tec.conf
sudo touch /var/log/php-fpm/tec-error.log
sudo chown tec:tec /var/log/php-fpm/tec-error.log
sudo chmod 0640 /var/log/php-fpm/tec-error.log
sudo restorecon -v /var/log/php-fpm/tec-error.log
sudo php-fpm -t
```

Preparar los contextos del directorio privado y de sesiones siguiendo README.md.
No inicializar JSON nuevos sobre datos existentes. Comprobar que el usuario tec
puede recorrer /var/log/php-fpm; preparar el log propio sin cambiar recursivamente
permisos de todo /var/www o los registros de otros pools.

El ejemplo establece listen.owner/nginx, listen.group/nginx y listen.mode/0660.
Si se usa listen.acl_users o listen.acl_groups, PHP-FPM ignora esos dos campos de
propietario/grupo. Inspeccionar la configuración y getfacl antes de combinar ACL
con modos. FPM debe recrear el socket con su política; no mantener un chmod 777
manual sobre /run/php-fpm/tec.sock.

```bash
sudo getfacl /run/php-fpm/tec.sock
sudo -u nginx test -r /run/php-fpm/tec.sock
sudo -u nginx test -w /run/php-fpm/tec.sock
sudo ausearch -m AVC,USER_AVC -ts recent
```

Los test de lectura/escritura comprueban permisos Unix; no sustituyen el análisis
de un AVC del dominio de Nginx. No desactivar SELinux para ocultar el fallo.

## 4. Validar y reiniciar

```bash
sudo php-fpm -t
sudo nginx -t
sudo systemctl restart php-fpm
sudo systemctl reload nginx
curl -I https://tec.1-s.es/
```

Un HTTP 503 de la aplicación requiere revisar el almacén privado; un 502 requiere
seguir el mensaje del upstream. Validar ambos alias y comprobar un formulario y
su sesión sin publicar phpinfo ni una consola administrativa en la web.

Referencia primaria: https://www.php.net/manual/en/install.fpm.configuration.php
