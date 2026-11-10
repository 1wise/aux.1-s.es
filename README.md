# AUX 7.0.0-beta.0

Timestamp: 2026-11-10 | Version: 7.0.0-beta.0  
Author & Credits: https://www.alawise.es/1-s

Entrega completa de la suite AUX: aplicaciones de consola, fuentes del portal,
instalador, perfiles Debian/Fedora, catálogo y recetas de imágenes. No requiere
parches. Es una beta para pruebas; no incluye una nueva ISO compilada.

## Aplicaciones de consola

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

Las instantáneas incluidas contienen 288 entradas, 186 de ellas menús externos,
y las tareas/grupos Debian/Fedora usados por los perfiles. Son datos conservados
de las fuentes anteriores, no un nuevo rastreo de red efectuado para esta beta.
Ver docs/CATALOG-7.md y config/software/README.md para procedencia y alcance.

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
