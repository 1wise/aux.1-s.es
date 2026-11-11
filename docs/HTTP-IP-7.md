# Comprobar el acceso Live por IPv4

Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
Author & Credits: https://www.alawise.es/1-s

La existencia de kernel, initrd y SquashFS no prueba su publicación HTTP.
En Excalibur se comunicó un HTTP 404 de Nginx para el fetch numérico de GParted.
La misma ruta fue accesible por el dominio PXE durante la comprobación externa.

Comparar desde el propio servidor la petición numérica y su variante con Host:

```bash
curl --noproxy '*' --max-time 10 -I \
  http://144.217.182.189/gparted-live-1.8.1-6-amd64/live/filesystem.squashfs
curl --noproxy '*' --max-time 10 -I -H 'Host: pxe.1-s.es' \
  http://144.217.182.189/gparted-live-1.8.1-6-amd64/live/filesystem.squashfs
```

Si la segunda petición funciona, revisar el bloque activo que sirve PXE en el
puerto 80. Nginx selecciona primero dirección/puerto y después el nombre Host.
Se puede declarar la IPv4 como un nombre adicional en ese bloque, usando la
misma raíz pública. Si ambas peticiones fallan, revisar también listen, root y
las reglas location antes de modificar server_name.

Localizar los archivos activos sin publicar toda la configuración:

```bash
sudo nginx -T 2>/dev/null | awk '
/^# configuration file / {archivo=$0}
/server_name.*pxe[.]1-s[.]/ {print archivo; print}
'
```

Una modificación de configuración requiere comprobar `sudo nginx -t` y repetir
el HEAD. No se debe dar un resultado de archivo local por una prueba de HTTP o
de arranque en el equipo cliente.

Documentación primaria: [server_names](https://nginx.org/en/docs/http/server_names.html)
y [request_processing](https://nginx.org/en/docs/http/request_processing.html).
