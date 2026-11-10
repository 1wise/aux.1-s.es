# AUX / PXE / TEC · 7.0.0-dev.4

Timestamp: 2026-11-10 | Version: 7.0.0-dev.4  
Author & Credits: https://www.alawise.es/1-s

Esta edición integra cuatro aplicaciones web: área de trabajo, instalador,
catálogo de descargas y entrada a sistemas. El instalador deja ISO como primera opción y sistema actual al final, con aviso explícito. aux-assist es un componente seleccionable. Permite escoger las
230 tareas nativas de Debian Testing o los 20 entornos y 155 grupos de Fedora
45, además de las herramientas AUX. La consola y los perfiles ISO consumen
la misma selección. Los catálogos son instantáneas oficiales de noviembre de 2026;
APT/DNF resuelven disponibilidad y dependencias en el sistema de destino.

```bash
sha256sum -c SHA256SUMS
python3 build.py --output dist --package-source
python3 aux-setup --interactive
```

La web generada está en `dist/`. El archivo descargado desde su instalador
permite revisar el plan con `python3 aux-setup --selection aux-selection.json`.
Añadir `--apply` ejecuta el plan. El menú de consola usa casillas de `dialog`
cuando está instalado y ofrece búsqueda numérica como alternativa.

| Componente | Función |
|---|---|
| `aux-setup` | Sistema actual, raíz nueva, ISO oficial personalizada, herramientas o servidor. |
| `aux-profile` | Tareas/entornos/grupos nativos y complementos AUX; Kickstart o preseed. |
| `aux-catalog` | Descubrimiento configurado, selección, sumas, publicaciones conservadas y listas light/heavy. |
| `aux-enter` | Detección local, inspección, desbloqueo y chroot de reparación. |
| `aux-tools` | Menú de aplicaciones locales, catálogo y Cockpit. |
| `aux-assist` | Controles físicos VT6, identidad persistente y asistencia autorizada. |
| `tec/`, `cli/` | Portal de técnicos y gateway con dos terminales retenidas. |

El modo `root` prepara una raíz; todavía requiere particiones, fstab, cuenta,
initramfs y cargador para obtener un disco arrancable. El modo `iso` añade
perfiles y fuentes a un instalador oficial verificado; necesita validación en VM.
No se incluye una ISO nueva compilada. Los servicios de asistencia se abren
manualmente. La configuración existente y los datos de trabajo son persistentes.

La construcción local no publica el Site anterior. La cuenta seleccionada no
permite acceder a ese Site y esta edición todavía no se ha enviado a GitHub.

[Despliegue y recorridos](docs/DEPLOY-7.md) ·
[Pruebas y aceptación pendiente](docs/CHECKS-7.md) ·
[Procedencia de tareas y grupos](config/software/README.md)

Las aplicaciones recuperadas de 6.4 mantienen la compatibilidad del protocolo.
Las guías históricas y el informe de pruebas de dev.2 se conservan identificados
como referencias, sin presentarlos como pruebas nuevas de esta edición.

El catálogo remoto añade 186 entradas netboot y 53 imágenes Fedora 45 en origen.
El rastreador actualiza metadatos; la descarga local requiere una lista de IDs y
límites de cantidad y bytes. Las copias previas se conservan y se reutilizan
sin duplicar el espacio. Ver [catálogo y almacenamiento](docs/CATALOG-7.md).
