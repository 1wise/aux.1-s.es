# Bastion / OVH — raíz pública completa B/P/T

Timestamp: 2026-10-17 | Version: 6.1.0-dev.1
Author & Credits: https://www.alawise.es/1-s

b.1-s.es/eu, p.1-s.es/eu y t.1-s.es/eu usan LA MISMA carpeta Multisite, por ejemplo
www/aux. No existe una raíz T separada. El despliegue entero, las ISO descargables,
los árboles extraídos y las páginas se transfieren allí como archivos físicos.
No se duplica una ISO para B y otra para P; se conservan las rutas del catálogo.

shared.htaccess elige B/AUX, P/PXE y T/TEC según el host, incluyendo endpoints y
assets relativos. No fuerza HTTPS global porque iPXE usa HTTP. TEC debe usarse
SOLO por HTTPS. Comprobar cookies y certificados antes de hacer failover.

Preparar un árbol completo de DISCO con los scripts independientes. Estas rutas
son una elección local, no una supuesta ruta real del hosting OVH:

```bash
bash deploy.sh disk --output /srv/aux-bastion/html --cache /var/www/aux.1-s.es/isos --user nginx --group nginx
bash generate.sh --target bastion --output /srv/aux-bastion/html --cache /var/www/aux.1-s.es/isos --tec off --user nginx --group nginx
python3 ovh/assemble.py --web-root /srv/aux-bastion/html --iso-dir /var/www/aux.1-s.es/isos --tec-web tec/web --output /srv/aux-bastion/upload-6.1
```

El último comando solo calcula inventario/tamaño. Repetir con --apply para crear
una copia completa en un destino NUEVO, con espacio suficiente. Los enlaces solo
pueden resolverse dentro de las raíces web/ISO; declarar un --allow-root concreto
para árboles externos autorizados. Nunca declarar / como raíz permitida.
Se rechazan secretos, datos de usuarios, logs, claves y manage.php en el árbol.
No publicar una copia parcial. No se realiza ninguna subida automática.

Transferir el CONTENIDO de upload-6.1, incluido .htaccess, a la carpeta Multisite
común. deploy.sh ftp también puede usar esa carpeta local como --output; mantener
FTPS y verificar el destino antes de transferir. Para enlaces TEC activos en el
catálogo, regenerar con TEC activado después de validar la instalación:
assemble.py no modifica las URL ni habilita el catálogo por sí solo.

TEC necesita configuración privada, JSON, sesiones, correo y secretos FUERA de
la raíz pública. Adaptar AUX_ASSIST_DATA_DIR, AUX_ASSIST_CONFIG y demás rutas al
plan PHP real; ver tec/README.md. Si no se puede proteger ese almacenamiento o
configurar correo, dejar TEC desactivado. El script solo copia tec/web, nunca
cuentas, claves o manage.php. No activar dos autoridades de usuarios en paralelo.

Solo Excalibur/Kamala ejecutan aux-cli. Kamala necesita acceso público independiente
y TLS propio. Ninguna sesión SSH viva migra automáticamente. Para contingencia
DNS, preparar también AUX/PXE/TEC sobre esa misma raíz con URL coherentes.
Ensayar navegación B/P/T, descargas y árboles con Excalibur apagado antes de anunciarlo.
