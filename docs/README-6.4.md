# AUX/PXE · WAN Arsenal 6.4.0-dev.1

Timestamp: 2026-10-24 | Version: 6.4.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

Este paquete contiene el catálogo AUX, los menús iPXE y las herramientas de
descarga, despliegue y generación. Puede usarse de forma independiente: cada
comando cumple una fase y ninguno encadena automáticamente los otros.

| Comando | Tarea |
| --- | --- |
| `download.sh` | Descargar imágenes al caché persistente |
| `deploy.sh ram` | Publicar recursos ligeros desde tmpfs |
| `deploy.sh disk` | Publicar copias y directorios extraídos en disco |
| `generate.sh` | Generar el portal, índice, menú iPXE y sitemaps |
| `deploy.sh ftp` | Replicar el árbol público y caché a Bastion mediante FTPS |

`fast-boot.json` define rutas y hosts; `CONFIGURATION.md` explica la
configuración. `light-url.txt` selecciona recursos para RAM, `heavy-url.txt`
los de disco y `url.txt` conserva la lista conjunta. La selección no garantiza
que un origen siga disponible ni que una imagen sea arrancable por PXE.

## Preparar el despliegue

Extraer el ZIP en un directorio de trabajo fuera de la raíz pública. Ajustar
la configuración con las rutas, dominios y almacenamiento reales. El caché
persistente y el árbol web son destinos distintos. Revisar primero las fases
sin cambios en disco ni descargas:

```bash
bash download.sh --list light --dry-run
bash deploy.sh ram --list light --dry-run
bash download.sh --list heavy --dry-run
bash deploy.sh disk --list heavy --dry-run
bash generate.sh --dry-run
```

Después de comprobar los destinos, ejecutar las fases seleccionadas en orden:

```bash
bash download.sh --list light --verbose
bash deploy.sh ram --list light --verbose
bash download.sh --list heavy --verbose
bash deploy.sh disk --list heavy --verbose
bash generate.sh --verbose
```

FTP es una operación aparte (`bash deploy.sh ftp --help`) que solicita la
contraseña fuera del JSON. Configurar previamente el alojamiento y su raíz
remota. El menú WAN Arsenal generado usa la URL PXE configurada. Los recursos
pesados completos pueden dirigirse a Bastion; cambiar el menú no altera el
estado de DNS, Nginx ni el contenido de una llave USB ya grabada.

Para revisar el comportamiento y las rutas de servidor, consultar
[DEPLOYMENT.md](DEPLOYMENT.md) y [TESTING.md](TESTING.md). Para los cambios de
esta entrega, leer [RELEASE-6.4.md](RELEASE-6.4.md) y
[INSTALL-6.4.md](INSTALL-6.4.md).
