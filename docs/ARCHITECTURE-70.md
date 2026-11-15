# AUX 70.0.1.beta.1 — Arquitectura y Guía Operativa

Timestamp: 2026-11-15 | Version: 70.0.1.beta.1
Author & Credits: https://www.alawise.es/1-s

## 1. Consola Unificada y Diálogos (`auxlib/console_ui.py` & `auxlib/interactive.py`)

El punto de entrada `./aux` centraliza las herramientas sin duplicar lógica ni mezclar permisos:

| Aplicación | Comando directo | Tema | Función principal |
|---|---|---|---|
| **AUX Config** | `./aux-config --interactive` | Índigo | Rutas, espejos SSH/FTPS, límites RAM/SSD y credenciales privadas. |
| **AUX Release** | `./aux-release --interactive` | Cyan | Inventario inmutable, transferencia sin copias, verificación remota y publicación. |
| **AUX Catalog** | `./aux-catalog --interactive` | Índigo | Rastreo de 49 reglas/30 fuentes, recuperación manual/API y perfiles de réplica. |
| **AUX Images** | `./aux-images --interactive` | Cyan | Instaladores ISO, perfiles Kickstart/preseed, recetas Live y medios USB. |
| **AUX Enter** | `./aux-enter --interactive` | Índigo | Inspección en solo lectura o rescate chroot sobre ext4/XFS/Btrfs/LUKS/LVM. |
| **AUX Setup** | `./aux-setup --interactive` | Cyan | Composición de perfiles e instalación controlada (ISO primero, host al final). |

### Navegación en `console_ui.py`
- **Panel izquierdo (`DISPONIBLES`):** Navega por categorías o lista plana, filtra en vivo con `/` y marca casillas con `Espacio`.
- **Panel derecho (`SELECCIONADAS` / `DETALLE DEL RECURSO`):** `Tab` conmuta el foco para desmarcar elementos elegidos o desplazar fichas técnicas largas (`PgUp`/`PgDn`) en terminales de 80x16.
- **Confirmación de planes (`campo_pantalla`):** Muestra el plan completo desplazable antes de aceptar la palabra clave de ejecución.

## 2. Flujo de Réplica y Corrección de `--input-root`

Para publicar en Bastion desde Excalibur sin duplicar los gigabytes de las ISOs:

```bash
./aux-config --interactive
./aux-release inventory --release-id v70-b1 --apply
./aux-release deploy    --release-id v70-b1 --apply
./aux-release verify    --release-id v70-b1 --apply
./aux-release generate  --release-id v70-b1 --apply
./aux-release publish   --release-id v70-b1 --apply
./aux-release verify    --release-id v70-b1 --apply
```

En `v70.0.1.beta.1`, `generate.sh` incorpora `ruta_permitida()` dentro de `arc_unidad()` y `obt_par()` para validar que los enlaces simbólicos de `input-view` apunten legítimamente a `source_root`, `cache` o `ram_dir` sin ser descartados por no residir físicamente bajo el directorio temporal de la vista.
