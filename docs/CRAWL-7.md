# Rastrear todas las descargas

Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

F5 en python3 aux-catalog -i revisa las 49 URL actuales con 30 grupos de fuentes.
La lista de entrada se elige en la cuarta pantalla; url.txt es el valor inicial.
No se descargan ISO, QCOW2, archivos de netboot ni cargadores durante el rastreo.

La cobertura declarada está en CRAWL-COVERAGE-7.json. Añadir una URL sin regla
produce una fila unmapped: no se asume que esa URL esté actualizada. El selector
conserva edición, arquitectura y canal. Las imágenes LTS, Testing, Beta y los
instaladores de 32 bits conservan sus ramas específicas.

| Fuente | Metadatos consultados |
|---|---|
| Debian | Índices current/live, archivo Bookworm i386, weekly Testing, cloud y netboot Bookworm. |
| Fedora | releases.json: Server netinst, Workstation Live y Cloud Generic en ambas arquitecturas. |
| Alpine | latest-releases.yaml de aarch64, x86 y x86_64. |
| Arch | API de publicaciones y cabeceras de los tres cargadores iPXE. |
| Gentoo | Punteros latest de minimal y LiveGUI y sus SHA-256. |
| Kali / Ubuntu / CentOS | Índices oficiales, manteniendo edición y rama. |
| Netboot.xyz | API de publicación estable de los dos cargadores; el inventario de menús se consulta aparte. |
| Clonezilla | Manifiesto de checksums del canal Testing. |
| GParted / Memtest / SystemRescue / Rescatux / Super Grub / Proxmox | Páginas oficiales de descargas e imágenes anunciadas. |
| Redo Rescue / Boot Repair | RSS de archivos de los proyectos en SourceForge. |

Estados de cada descarga:

- resolved: se identificó una versión de la edición/canal solicitados en la fuente.
- rolling-checked: la URL de contenido variable responde con un archivo; no se inventa una nueva versión.
- failed: no se pudo resolver la fuente o la edición. Se muestra el error.
- unmapped: falta una única regla para esa URL de entrada.

El resultado HTTP y la disponibilidad del tamaño son campos independientes.
Una versión resuelta no garantiza que un espejo responda en el momento de descargar.
El checksum anunciado no significa que se hayan verificado bytes de una imagen.
Los tamaños ausentes siguen siendo desconocidos. Las firmas PGP no se comprueban.
No se guardan tickets temporales de los espejos en los informes públicos.

Super Grub Beta tiene una política explícita latest_available: si una versión
anunciada devuelve 404/410, se consulta la anterior del mismo canal y se indican
las versiones descartadas. No se cambia de Beta a Stable ni de arquitectura.

Siempre se guarda state/catalog/crawl-report.json. Si falla una descarga,
no se sustituye current ni se sincronizan las listas; el informe conserva las
49 filas. Si termina correctamente, Sincronizar listas locales muestra el diff,
pide APLICAR y guarda copias *.before-crawl. La revisión no descarga imágenes.

```bash
python3 aux-catalog --config config/catalog.sources.json \
  --output state/catalog --cache state/catalog-http --url-file url.txt
python3 aux-catalog --sync-lists --output state/catalog
```

El segundo comando sólo muestra el diff; --apply lo aplica. El CLI de download
conserva su verificación SHA-256 explícita mediante --checksums. El informe del
crawler no sustituye la verificación del archivo descargado ni una prueba de arranque.

## Redirecciones de espejos en beta.3

mirror_redirect_origins declara los redireccionadores de descarga que pueden
delegar la comprobación de una imagen: download.fedoraproject.org para Fedora,
y cdimage.kali.org/kali.download para Kali. La petición inicial sigue limitada
a los hosts de su fuente. La delegación no se aplica a índices, API ni fuentes
sin esa configuración. Los destinos deben usar HTTPS sin credenciales y sus
direcciones DNS deben ser públicas de unicast.

La comprobación conserva HEAD durante toda la cadena; un servidor que rechaza
HEAD con 405/501 conserva el fallback Range sin leer el cuerpo. El campo
redirect_policy indica provider-delegated-https o configured-hosts. Un error
DNS, TLS, HTTP o de tamaño sigue apareciendo como fallo, por separado de resolver
la versión. Este resultado no verifica el hash del archivo descargado.
