# AUX 8.0.1-beta.3 — tamaños y continuidad de deploy

Timestamp: 2026-11-23 | Version: 8.0.1-beta.3  
Author & Credits: https://www.alawise.es/1-s

Deploy completa los metadatos pendientes antes de calcular la capacidad. La beta.2 detenía todo el lote si el catálogo local carecía de un tamaño, aunque la imagen ya estuviese descargada y el catálogo publicado lo tuviera resuelto.

Si existe un SHA-256 esperado, se verifica el archivo completo de caché y se obtiene su tamaño real. Se admiten la ruta de artefactos y la antigua caché plana. Esta observación local no se presenta como un checksum oficial nuevo. Un archivo parcial o sin checksum esperado no sirve para autenticar la imagen.

Cuando faltan metadatos y C permite resolver y rastrear, se consulta el origen mediante las reglas configuradas. Se conservan las políticas, prioridades y sectores manuales. Una versión ya autenticada no se sustituye por la más reciente durante deploy: ese cambio requiere catalog refresh y download expresos. Los metadatos completos no se refrescan por estar en una URL mutable. Deploy no descarga las imágenes.

El catálogo actualizado y su SHA-256 se guardan antes del cálculo. Los recursos sin tamaño o checksum comprobable quedan pendientes y aparecen en el informe; no se presupuestan como cero ni se despliegan. El resto continúa dentro de los límites configurados. Los fallos por recurso o destino tampoco interrumpen los demás; los conflictos globales de presupuesto mantienen el bloqueo.

El informe deploy-report.json se guarda junto al status_file configurado, con el ID, destino, etapa, resultado y error. La salida conserva progreso por recurso y un resumen final. Cualquier fallo devuelve código 1; conviene revisar el informe antes de ejecutar checkstatus y generate. Un deploy correcto no acredita arranque hasta login.

Tras actualizar las fuentes a beta.3, repetir la selección habitual de deploy. Si falta la imagen, ejecutar antes download. El plan sin --apply y cualquier --dry-run siguen sin consultas de red ni escritura de catálogo.

| ID estable | Recurso |
| --- | --- |
| other-tool-x86_64-nixos-minimal-26 | NixOS Minimal 26.05, x86_64 |
| other-tool-x86_64-agama-installer | Agama Installer, openSUSE Leap 16.0, x86_64 |

No es necesario cambiar casillas de disponibilidad o estado para resolver tamaños. A/S siguen siendo observaciones; las políticas C/D/E y prioridades P se conservan.

Validación: 510 casos Python, 491 ejecutados correctamente y 19 omitidos; trece pruebas nuevas de recuperación, conservación de versiones, los dos resolutores afectados, copia local y continuidad del lote. No se han desplegado las distribuciones en los servidores del proyecto.
