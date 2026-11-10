# Nginx: zona aux_pair duplicada

Timestamp: 2026-11-10 | Version: 7.0.0-dev.3  
Author & Credits: https://www.alawise.es/1-s

El instalador escribe /etc/nginx/conf.d/aux-cli.conf. Un vhost CLI anterior,
como cli.1-s.es.conf, puede declarar la misma zona. Nginx necesita una única
declaración limit_req_zone para aux_pair en http; las ubicaciones conservan
su uso de limit_req zone=aux_pair.

Localizar declaraciones antes de editar:

```bash
sudo grep -RnsE '^[[:space:]]*limit_req_zone[[:space:]]+.*zone=aux_pair:' /etc/nginx
```

Si aparecen dos declaraciones activas en archivos distintos, conservar una y
comentar la repetida de cli.1-s.es.conf. Guardar una copia fuera de conf.d antes
de editar. Si sólo existe una declaración, comprobar si su archivo o directorio
se incluye dos veces desde nginx.conf u otros archivos incluidos.

```bash
sudo nginx -t && sudo systemctl reload nginx
```

El parche añade una comprobación nginx -T antes de modificar usuarios o archivos
con --nginx. Rechaza tanto una configuración ya inválida como una zona aux_pair
activa fuera del archivo aux-cli.conf que administra. La integración de vhosts
existentes sigue siendo manual para conservar certificados y ajustes locales.

Validación local: 43 pruebas unittest aprobadas, incluidas cinco regresiones de
esta comprobación. No se ha ejecutado el parche en el servidor de producción.
