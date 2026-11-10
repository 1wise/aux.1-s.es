# Catálogo remoto y almacenamiento local limitado

Timestamp: 2026-11-10 | Version: 7.0.0-beta.0  
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
aux-catalog --interactive. El menú usa cyan e índigo en terminales con color;
en terminales de 8 colores usa azul y conserva una alternativa monocroma.
El menú principal agrupa distribuciones por familia
y herramientas por categoría; también permite ver todas las entradas o la
selección actual. Enter abre un menú o el selector light/heavy/solo origen de una entrada; Retroceso vuelve al anterior. Usa flechas
y AvPág/RePág para desplazarse, espacio para marcar, / para buscar en la lista
actual, L/H/R para elegir light/heavy/solo origen y O para ver la URL completa. S exporta
JSON y listas de origen; Q cancela. Las marcas se conservan entre menús. Los tamaños desconocidos aparecen por separado.
Las sumas expresan tamaños de archivo conocidos: la expansión y otros consumos
de RAM y disco necesitan espacio adicional. El presupuesto RAM y su reserva se
leen de fast-boot.json; la RAM disponible corresponde al equipo local. El espacio
libre de disco corresponde al directorio cache configurado, si existe en ese equipo.
Los menús externos aparecen como ORIG y quedan en el JSON, sin incluirse en
las listas de imágenes light/heavy; las opciones solo origen se escriben en origin-url.txt. No se descarga nada al exportar.
El servicio semanal incluido sólo ejecuta el comando
de metadatos; su instalación y activación en Excalibur no se han comprobado.
El adaptador netboot requiere python3-pyyaml en Fedora o python3-yaml en Debian.


## Presets y presupuesto del selector

Al abrir aux-catalog --interactive se aplica Default, definido por las URL
exactas de light-url.txt y heavy-url.txt del proyecto. Se conservan esas entradas;
si falta un tamaño o no cabe una copia local, queda solo origen y el JSON retiene
requested_selection_mode con la clase solicitada. No se presume que ocupe cero.

P abre tres presets: Default, Sugerido y Custom. Sugerido prioriza una entrada por
familia para instalación y rescate: Rescatux, SystemRescue, Clonezilla, GParted,
Memtest86+, Super Grub, netboot, Debian, Fedora, Alpine, Arch, Ubuntu y Proxmox.
Rescatux incorpora funciones de restablecimiento de contraseñas locales Windows:
https://www.supergrubdisk.org/rescatux/ . No se afirma recuperación de la contraseña
original ni desbloqueo de BitLocker o cuentas Microsoft.
Custom conserva la selección manual durante la sesión al cambiar de preset.
S exporta la selección y el preset con los límites en el JSON; no inicia descargas.

El panel izquierdo navega por el catálogo y el derecho muestra la selección.
Tab cambia de panel; espacio marca o quita; Enter abre submenús o el selector de
modo; L/H/R cambia el modo; A selecciona todo el grupo o lista visible (todo el
catálogo desde la raíz). A respeta lo ya elegido y agrega como origen las entradas
sin tamaño o sin espacio. Q cancela. Los indicadores L/H/O significan light,
heavy y origen; ?G indica tamaño desconocido.

fast-boot.json fija ram_budget_gib=28 y ssd_budget_gib=100. Se mantiene la reserva
de RAM del 10%: 25.2 GiB útiles. Todas las imágenes locales, incluidas light,
cuentan para SSD; sólo light cuenta para RAM. Se comprueba cada cambio y la
exportación. Son presupuestos de archivos del despliegue previsto: no sustituyen
el cálculo de expansión, el espacio ya ocupado ni la RAM del sistema arrancado.
El despliegue conserva sus comprobaciones físicas independientes.
