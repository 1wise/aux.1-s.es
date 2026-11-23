# Distribución por módulos

Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
Author & Credits: https://www.alawise.es/1-s

| Paquete | Servicios propios | Independencia |
| --- | --- | --- |
| aux-pxe | Portal gráfico, catálogo para Links, guías, iPXE, ISO y herramientas AUX | No instala TEC, PHP-FPM ni el gateway CLI. Puede enlazar con una comunidad externa. |
| tec-cli | Cuentas TEC, asistencia, terminal web, registro privado y foro PHP | No necesita generar ni alojar el catálogo AUX/PXE. AUX puede estar en otro servidor. |

Cada ZIP se extrae en un directorio vacío. Ambos incluyen el instalador y su
configuración de referencia. También pueden extraerse juntos; los archivos
compartidos son idénticos. La suite completa conserva los dos módulos y el código
de herramientas. No se incluyen ISO, secretos, cuentas, sesiones ni datos del foro.

Planes, sin privilegios y sin modificar el sistema:

```sh
python3 install-web.py --modules aux-pxe
python3 install-web.py --modules tec-cli
python3 install-web.py --modules aux-pxe tec-cli
```

En el servidor de referencia, revisar dependencias y rutas antes de añadir
`--apply`. `--nginx` instala únicamente los vhosts de la selección y comprueba
TLS y conflictos antes de modificarlos. La instalación integrada anterior se
conserva al seleccionar ambos módulos. Una actualización de un único módulo no
elimina los archivos, datos o servicios del otro.

La raíz de fuentes queda separada de `html/` (AUX/PXE) y `web/` (TEC).
Publicar solamente esas raíces. Los JSON de TEC se guardan en el directorio privado
configurado, fuera de ambas; hacer una copia privada antes de actualizar.

El foro nativo se abre en `forum.php` y reutiliza las cuentas TEC confirmadas.
Las recetas y respuestas quedan pendientes de revisión. Configurar moderación
desde el servidor con una cuenta confirmada:

```sh
php manage.php users
php manage.php forum-moderator usr_ID
php manage.php forum-unmoderator usr_ID
```

El foro PHP guarda `forum.json` con bloqueo y reemplazo atómico. No requiere
Node, Cloudflare, D1 ni una cuenta ChatGPT. El adaptador usado por la publicación
en Sites es independiente; su base de datos y usuarios no se sincronizan con TEC.
Una receta publicada continúa necesitando validación antes de importar su arranque
al catálogo. Mantener TEC/CLI y su estado privado fuera de la réplica de ISO.

Generar paquetes desde las fuentes completas:

```sh
python3 package-modules.py --output ./packages
```

Los ZIP contienen un manifiesto del módulo y un inventario SHA-256 interno. Las
sumas externas verifican los bytes de cada descarga; no son firmas de proveedor.

La réplica AUX/PXE genera sus guías y estilos completos. Los enlaces de paquetes
solo se ofrecen si los archivos están presentes en `html/downloads/`; copiar allí
los ZIP y sus sumas, y regenerar para anunciar las descargas de esa réplica.
