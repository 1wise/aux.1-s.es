# Despliegue y réplica

Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
Author & Credits: https://www.alawise.es/1-s

Orden directo: Settings → catálogo → download → deploy → generate.
`download.sh` obtiene las listas seleccionadas; `deploy.sh ram|disk|ftp`
prepara sus medios; `generate.sh` inspecciona los archivos y publica el portal,
catálogos de texto, contenido de imágenes, menu.ipxe y sitemaps.

Consultar antes los planes:

```bash
bash download.sh --list light --dry-run
bash deploy.sh ram --list light --dry-run
bash generate.sh --dry-run
```

La réplica por fases se abre con `python3 aux-release --interactive`.
La secuencia es inventory, deploy, verify, generate, publish y verify.
Sin --apply, el CLI presenta el plan. El menú muestra el efecto y requiere
APLICAR; una entrada incorrecta conserva el plan. Los fallos de comprobación
impiden avanzar a la publicación como si la transferencia hubiera terminado.

Excalibur y Bastion conservan el espejo público íntegro. La prioridad de
Excalibur para PXE/RAM y Bastion para descargas completas es una política de
servicio, no una exclusión de archivos del espejo. No replicar secretos ni
estado privado de TEC/CLI. FTP/FTPS transfiere los medios antes de anunciar
los índices generados. rsync sobre SSH conserva el mismo criterio.

Validar las rutas y el inventario reales. No publicar directorios de código
como raíz web. `--input-root` permite generar en un OUTPUT separado leyendo
medios preparados; los enlaces sólo pueden resolver dentro de las raíces
INPUT, caché y RAM autorizadas. La verificación remota SHA-256 lee los bytes
del espejo; no equivale a una firma oficial ni a un arranque físico.
