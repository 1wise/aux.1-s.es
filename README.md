# AUX 7.0.0-beta.15

Timestamp: 2026-11-10 | Version: 7.0.0-beta.15  
Author & Credits: https://www.alawise.es/1-s

Entrega completa de la suite AUX: aplicaciones de consola, fuentes del portal,
instalador, perfiles Debian/Fedora, catálogo y recetas de imágenes. No requiere
parches. Es una beta para pruebas; no incluye una nueva ISO compilada.

## Aplicaciones de consola

La beta.6 muestra también las referencias de origen en la portada y en las
vistas de texto. El taller se abre con `python3 aux-catalog --recipes -i`;
reutiliza las imágenes publicadas y conserva los modos elegidos. Cada receta
requiere aprobación individual antes de incorporarse al menú. El registro público
está en recipes.html / recipes.json. La propuesta de seguimiento con cuentas y
cuotas de API está documentada en [docs/RECETARIO-7.md](docs/RECETARIO-7.md).
El foro dinámico y los cobros no están implementados en esta entrega.

Cada aplicación muestra su nombre y función en cabecera. Configuración sobre
fondo índigo; instalación y generación sobre fondo cyan. Terminal con color,
Python 3.10+ y curses; para el catálogo usar al menos 100 columnas por 18 filas.
Los diálogos compartidos funcionan desde 80 columnas por 16 filas.

| Aplicación | Abrir | Fondo |
|---|---|---|
| AUX Catalog | python3 aux-catalog --interactive | Índigo |
| AUX Setup | python3 aux-setup --interactive | Cyan |
| AUX Profile | python3 aux-profile --interactive | Cyan |
| AUX Images | python3 aux-images --interactive | Cyan |
| AUX Enter | python3 aux-enter --interactive | Índigo |
| AUX Tools | python3 aux-tools --interactive | Índigo |
| AUX Download | bash download.sh -i | Cyan |
| AUX Deploy | bash deploy.sh -i | Cyan |
| AUX Generate | bash generate.sh -i | Cyan |

Flechas desplazan; Enter abre o acepta; espacio marca; Tab cambia al panel de
selección; S conserva las casillas; Q/Esc cancela. Retroceso vuelve de un grupo.
/ busca. Los campos admiten Ctrl+U para limpiar y Esc para cancelar. Los planes
largos pueden desplazarse antes de escribir APLICAR o GENERAR.

Setup ofrece ISO primero y sistema actual al final, con aviso explícito.
aux-assist es un componente seleccionable. Se conserva el CLI para automatizar.
Sin --apply, el CLI de instalación presenta un plan. El recorrido interactivo
pide confirmación antes de aplicar una instalación o construir una imagen.

AUX Images abre los generadores específicos: instalador ISO oficial, perfiles
Kickstart/preseed, receta Live y archivo de imagen USB. Una receta Live no es una
ISO compilada; el generador USB no graba dispositivos físicos.

También pueden abrirse directamente:

```bash
python3 iso-assist/prepare.py --interactive
python3 iso/prepare.py --interactive
python3 usb/portable/build.py --interactive
```

## Catálogo

Catálogo de dos paneles, menús por familia/categoría y tres presets: Default
(listas AUX actuales, aplicado al abrir), Sugerido (instalación y rescate, con
Rescatux) y Custom (selección manual conservada durante la sesión).

RAM configurada: 28 GiB, 25.2 GiB útiles con la reserva del 10%. SSD: 100 GiB,
incluidas las copias light. Las opciones sin tamaño conocido o sin espacio quedan
solo origen. A selecciona todo el grupo/lista visible; desde la raíz abarca el
catálogo. S exporta JSON y listas light/heavy/origen; no inicia descargas.
Los límites miden archivos, no la expansión ni el consumo del SO arrancado.

La raíz del catálogo ofrece **Rastrear / actualizar todas las descargas** (F5),
**Sincronizar listas locales** e **Informe del último rastreo**. El rastreo lee
la lista elegida (url.txt por defecto) y aplica 49 reglas a 30 grupos de fuentes.
Incluye todas las distribuciones, imágenes cloud, cargadores y herramientas de
las listas light/heavy actuales; no se limita a Debian/Fedora/Gentoo.
Consulta índices, API, manifiestos, checksums y cabeceras HTTP; no descarga imágenes.
Una URL añadida sin regla aparece como unmapped y no se omite en el informe.

El informe separa versión resuelta, URL de contenido variable comprobada,
disponibilidad HTTP, tamaño conocido y errores. Las ediciones, arquitecturas y
canales se conservan. Super Grub Beta permite buscar la versión disponible más
reciente de su canal y muestra las versiones anunciadas que ya no existen.
Los índices y API conservan sus hosts autorizados. Para las descargas de Fedora
y Kali se admiten los espejos HTTPS públicos elegidos por sus redireccionadores
configurados; no hace falta enumerar los espejos de cada país. La consulta
conserva HEAD al redirigir y registra la política usada en el informe.

La configuración incluida usa state/catalog/current y guarda siempre
state/catalog/crawl-report.json, incluso cuando una fuente falla. Un rastreo
incompleto conserva current y las listas, e impide sincronizar un resultado
anterior como si fuera el último. Sincronizar muestra el diff y requiere APLICAR;
conserva *.before-crawl. Las 49 reglas actualizan URL sin cambiar sus clases ni
convertir todo el catálogo remoto en una selección local. Ver docs/CRAWL-7.md.

download, deploy y generate admiten -i y --interactive. La interfaz ejecuta
primero el --dry-run real y muestra sus resultados y el comando completo. Sólo
EJECUTAR permite salir del plan hacia la tarea. --dry-run -i conserva siempre
la simulación. El perfil Excalibur/Bastion cambia las URL; la tarea se ejecuta
en el equipo local. La contraseña FTP se solicita oculta al iniciar la transferencia.

menu.ipxe incorpora **Systems and tools / full origin catalogue** con familias
y categorías del catálogo. Los menús remotos se agrupan por URL (el proveedor
elige la versión), cargan boot.cfg y luego el menú seleccionado por HTTPS.
Las imágenes ISO/QCOW2 sin receta sólo muestran su URL. Se incluye acceso al
menú completo del proveedor. No se descarga ninguna imagen al generar el menú.

La instantánea web incluida conserva 289 entradas y 186 referencias a 102 menús
remotos distintos. El nuevo rastreo cubre las 49 descargas de las listas locales;
su informe y publicación se crean en el equipo donde se ejecuta. La instantánea
incluida no se presenta como una comprobación nueva de todas esas URL.
Ver docs/CATALOG-7.md y docs/CRAWL-7.md para procedencia y alcance.

Las tareas/grupos de instalación conservan su catálogo de software previo.

## Perfiles de réplica y asistencia GPT/Gemini

El menú de aux-catalog -i añade asistencia API para proponer selecciones, fuentes
y recetas iPXE, y un editor de perfiles manual sin API. Default/Sugerido/Custom
se conservan; cada réplica puede guardar sus modos light/heavy/origen, presupuestos
y un Default propio, sin reescribir los defaults distribuidos de AUX.

Las propuestas se verifican y revisan antes de EXPORTAR o ACTIVAR. Las claves se
piden sin eco o se leen del entorno seleccionado; no se guardan en perfiles ni web.
La API no descarga imágenes ni ejecuta órdenes. El perfil exporta sus listas, su
configuración de crawler y un menú de recetas revisadas. generate --catalog-profile
incorpora esas recetas al menu.ipxe con aviso de arranque aún sin probar.

Ver docs/CATALOG-API-7.md para modelos, revisión, perfiles portátiles y comandos.
La beta también permite la redirección HTTPS del manifiesto de checksums de Kali
mediante la política ya declarada para su servidor de descargas.

## Construir la web para publicar

```bash
sha256sum -c --quiet SHA256SUMS
python3 build.py --output dist --package-source
```

La web queda en dist/, con release-7.html, las aplicaciones web y paquetes
completos ZIP/TAR.GZ en downloads/. La interfaz menuconfig es de terminal; el
catálogo web conserva su tabla HTML y sus enlaces de origen. La construcción
no publica un servidor ni envía cambios a GitHub.

## Pruebas y límites de la beta

```bash
python3 -m unittest discover -s tests7 -q
```

El instalador de clientes requiere el gestor y repositorios de la distribución
de destino. Las recetas ISO requieren xorriso y un medio oficial verificado.
La raíz nueva aún necesita particiones, fstab, cuentas, initramfs y cargador.

Pendientes: instalación real Fedora/Debian, pruebas BIOS/UEFI/Secure Boot,
LUKS/chroot en VM, temporizador en Excalibur, despliegue remoto y páginas de
redirección automáticas para las entradas solo origen. Los servicios de
asistencia se activan explícitamente; no se abre una sesión remota al seleccionar
un perfil. Los componentes recuperados de 6.4 conservan sus versiones internas
cuando siguen siendo recetas históricas; no se presentan como nuevas ISO beta.

[Notas de beta](RELEASE-7.md) · [Comprobaciones](docs/CHECKS-7.md) ·
[Norma visual](docs/CONSOLE-7.md) · [Despliegue](docs/DEPLOY-7.md)
