# AUX Suite · v70.0.1.beta.1

Timestamp: 2026-11-15 | Version: 70.0.1.beta.1
Author & Credits: https://www.alawise.es/1-s

Punto de inicio limpio para el ciclo **v70.0.1.beta.1**. Se ha purgado el lastre documental e histórico de las series 5.x, 6.x y betas previas (`RELEASE-6*.md`, `INSTALL-6*.md`, `TEST-6*.md`, `CHECKLIST-6*.json`, `BASELINE-19.json`, `verify-v6*.py`), unificando la arquitectura, las referencias de versión y los comentarios en estilo Linux bajo el estándar 1wise.

## Arquitectura Unificada

1. **Consola Unificada (`./aux` y `auxlib/console_ui.py`):**
   - Fondo **índigo** para configuración, catálogo y enrutamiento; fondo **cyan** para instalación, construcción de imágenes y despliegue.
   - Selectores de doble panel (`menuconfig`) con soporte nativo `curses`, búsqueda en vivo (`/`), árbol de grupos, vista de detalles lateral y alternativa limpia en TTY o `dialog`.
2. **Ciclo de Réplica Sin Copias (`./aux-config` y `./aux-release`):**
   - Separación estricta entre `INPUT` (`/var/www/aux.1-s.es/html` + `/var/www/aux.1-s.es/isos`) y `OUTPUT` de trabajo.
   - Vistas enlazadas (`input-view`, `deploy-view`) transferidas vía `rsync` sobre SSH o FTPS explícito, con verificación remota de SHA-256 real.
   - Resolución de enlaces simbólicos inter-raíz corregida en `generate.sh` (`ruta_permitida`) para que `--input-root` valide kernels e initrds sin rechazar enlaces hacia la caché o RAM.
3. **Estándar de Código y Comentarios (1wise):**
   - Cabeceras canónicas con `Timestamp`, `Version: 70.0.1.beta.1` y `Author & Credits: https://www.alawise.es/1-s`.
   - Comentarios técnicos en inglés (US English), estilo kernel de Linux: directos, explicando el *porqué* de cada invariante y diseñados para invitar a estudiar y bifurcar el código.

## Estructura de Documentación Vigente

| Documento | Propósito |
|---|---|
| `README.md` | Punto de entrada general y resumen de arquitectura v70.0.1.beta.1. |
| `AGENTS.md` | Convenciones de interfaz, temas de consola y reglas de código. |
| `docs/ARCHITECTURE-70.md` | Guía unificada de operación: consola, catálogo, réplica y medios Live. |
| `scripts/upgrade-to-70.0.1.beta.1.sh` | Script idempotente para limpiar el árbol `beta.20`, fijar la versión y actualizar `SHA256SUMS`. |
