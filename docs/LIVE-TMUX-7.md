# Configuración tmux dentro de la Live

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

La configuración de la terminal debe formar parte del medio de arranque. Crear
el archivo en la RAM de una Live ya iniciada permite continuar la prueba, pero
ese cambio no modifica la ISO que se está usando.

## Archivos de la imagen

La receta integra /usr/share/aux-assist/tmux.conf, modo 0644, desde config/tmux.conf.
Las aplicaciones completas conservan otra copia en
/usr/local/lib/aux/config/tmux.conf. Ambas proceden del manifiesto verificado de
la entrega. El postinstalador exige que los contenidos coincidan antes de terminar.

La preparación añade tmux_config_sha256 a source-manifest.json. El finalizador
extrae /LiveOS/squashfs.img de la ISO y lee usr/share/aux-assist/tmux.conf con
unsquashfs -cat. No monta la imagen ni ejecuta su contenido. Si falta el archivo,
está vacío o su SHA-256 difiere, se detiene antes de crear la ISO final.

Sólo después de esa comprobación aux-live.json declara tmux_config_verified=true.
boot_verified permanece false: comprobar un archivo no sustituye el arranque ni
la aceptación de BIOS/UEFI o Secure Boot. El constructor requiere unsquashfs,
incluido en squashfs-tools, antes de iniciar el trabajo KVM.

Las recetas y manifiestos anteriores sin tmux_config_sha256 deben regenerarse
con la misma versión del constructor antes de utilizar el finalizador nuevo.
Conservar el instalador Fedora netinst ya verificado; no es necesario descargarlo
de nuevo para preparar otra salida de construcción.

## Recuperación al iniciar la Live

El cliente conserva cualquier tmux.conf existente. Si falta la configuración
predeterminada de una Live genérica, la recupera de la copia pública de las
aplicaciones, con escritura completa y publicación atómica. No reemplaza un
archivo creado a la vez por otra operación ni inicia terminales durante la recuperación.

Si faltan ambas copias, presenta un error claro antes de llamar a tmux. Una ruta
explícita ausente y la configuración ausente de un sistema instalado requieren
revisión; no se reemplazan silenciosamente con una configuración genérica.
La misma preparación se usa al crear las dos terminales y la sesión SSH directa.

Para identificar el medio actualmente arrancado, en la Live:

```bash
cat /run/initramfs/live/aux-live.json
```

Ese manifiesto procede de la ISO. Actualizar las aplicaciones o tmux.conf en RAM
no cambia la versión que declara el medio. La nueva salida debe compilarse en
un directorio distinto y comprobarse antes de reemplazar el medio anterior.

## Ensayos de la entrega

- Ocho pruebas de recuperación con archivos reales: ausencia, conservación,
  permisos con umask 077, configuración explícita, sistema instalado, falta de
  origen, interrupción de publicación y creación simultánea.
- Comprobaciones del postinstalador para ausencia, symlink, contenido distinto
  y permisos incorrectos del archivo integrado.
- Cuatro imágenes ISO/squashfs mínimas reales: archivo correcto, ausente,
  modificado y rechazo del finalizador antes de crear una salida final.
- El conjunto principal mantiene la comprobación de que el manifiesto no
  presenta como arrancada una ISO que no se ha ensayado.

No se han ejecutado Lorax ni una VM de la ISO beta.16 en este entorno.

Referencias de formato: [Live x86 de Lorax](https://github.com/weldr/lorax/blob/master/share/templates.d/99-generic/live/x86.tmpl)
y [formatos squashfs de Lorax](https://github.com/weldr/lorax/blob/master/docs/lorax.rst).
