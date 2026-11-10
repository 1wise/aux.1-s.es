# Catálogo remoto y almacenamiento local limitado

Timestamp: 2026-11-10 | Version: 7.0.0-dev.4  
Author & Credits: https://www.alawise.es/1-s

El catálogo web ofrece el abanico de menús netboot del proveedor y sus enlaces
de origen. La instantánea del 2026-11-10 contiene 186 entradas de menús/versiones
netboot y 53 imágenes Fedora 45 en origen, además de las referencias de la suite.
Son enlaces y metadatos; no se incluyen ni se descargan esas imágenes.
Las entradas externas y sus arquitecturas proceden del proveedor. El estado
upstream no sustituye pruebas BIOS/UEFI de AUX y sus recetas verificadas.
Los enlaces individuales de menús permiten consultar sus scripts; el arranque
completo se realiza desde el cargador y el menú principal de netboot.xyz.

El rastreador consulta índices conocidos con caché HTTP y genera publicaciones
completas antes de sustituir current. El ejemplo consulta Debian Testing, el
JSON oficial de versiones Fedora y la configuración e inventario netboot.xyz.
Fedora se contrasta con su índice oficial: netboot.xyz todavía listaba Fedora
44 en su configuración al consultar la instantánea, mientras Fedora ya publica
45. Se conserva esa procedencia; no se renombra un menú 44 como si fuese 45.
La versión del instalador y su catálogo de grupos quedan fijados en Fedora 45;
Rawhide permanece separado, conservado como referencia de metadatos.

```bash
python3 aux-catalog --config config/catalog.sources.example.json --cache /tmp/aux-catalog-cache --output /tmp/aux-catalog-preview
```

El comando actualiza metadatos y enlaces. Para descargar localmente se añade
--download, y la configuración debe declarar explícitamente:

- storage.enabled: true.
- storage.ids: IDs de las imágenes concretas elegidas del catálogo.
- storage.max_images: cantidad máxima de archivos de imagen locales.
- storage.max_total_bytes: presupuesto total de bytes de imágenes.

El ejemplo deja la descarga desactivada, la selección vacía y el presupuesto
sin asignar. Su límite ilustrativo de dos imágenes no sustituye una decisión
sobre qué distribuciones o cuánto espacio reservar. Los menús externos tienen
remote_only=true y no pueden entrar en la caché de imágenes. La selección local
no reduce el catálogo remoto publicado.

Los límites incluyen las imágenes de publicaciones anteriores. Se reutilizan
copias idénticas verificadas mediante enlaces duros, sin repetir su espacio.
Una actualización de metadatos conserva las copias locales previas. Si no cabe
una imagen nueva, la operación conserva la publicación anterior; no elimina
imágenes comprobadas para hacer sitio. La rotación de las imágenes antiguas
requiere revisar la selección y el espacio reservado.

La publicación está en current/index.html y current/catalog.json. La tabla
HTML funciona sin JavaScript en Links/Lynx. El menú de consola se abre con
aux-catalog --interactive. El servicio semanal incluido sólo ejecuta el comando
de metadatos; su instalación y activación en Excalibur no se han comprobado.
El adaptador netboot requiere python3-pyyaml en Fedora o python3-yaml en Debian.
