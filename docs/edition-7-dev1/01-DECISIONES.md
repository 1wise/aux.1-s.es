# Decisiones de la edición 7

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Decisión definitiva sobre el sistema

La unidad de trabajo será un sistema instalado de forma convencional. Se
mantienen su gestor de paquetes, bases de datos, permisos y configuración en un
sistema de archivos persistente. Se descarta el overlay Live como arquitectura
principal después de los problemas observados con el arranque persistente.

El kernel será el de la distribución, con módulos y firmware suficientes para
varios equipos. El initramfs debe ser genérico, sin depender exclusivamente del
hardware del constructor. No existe una necesidad general de compilar un kernel
especial por el mero hecho de que el sistema vaya en USB.

La RAM se aprovechará mediante la caché normal del sistema y temporales
controlados. No se prometerá que un ajuste de kernel elimina la lentitud física
de una memoria USB. No se coloca la raíz instalada completa en tmpfs ni se
reconstruye un SquashFS para guardar cambios.

## Productos y ramas

- Debian Testing: `aux.iso` como instalador y disco instalado Debian.
- Fedora de desarrollo: `pxe.iso` como instalador y disco instalado Fedora.
- `tec.img`: cargador de arranque iPXE.
- AUX Assist: componente común previsto en las instalaciones completas.
- XFCE: escritorio previsto en ambas ediciones.
- Arquitectura inicial de las instrucciones: x86_64/amd64.

Debian Testing está decidido. Rawhide es el valor de trabajo propuesto para
Fedora en los ejemplos; la elección definitiva de Rawhide o Branched debe
quedar registrada antes de publicar. `updates-testing` no es un nombre de
distribución equivalente a Debian Testing. Registrar la instantánea concreta
de los repositorios y los paquetes realmente instalados.

## Experiencia de asistencia

Se ofrecerán Cockpit y SSH. SSH podrá utilizarse desde terminal web o cliente
convencional con clave pública. La presencia de Cockpit no obliga a utilizarlo
para abrir una terminal de rescate local. La red puede estar caída sin impedir
el acceso al escritorio o a las herramientas locales.

Se incorporarán 20.000 líneas de historial y ratón en tmux. El desplazamiento
mediante rueda ha funcionado en la sesión observada. La barra del terminal web
y Shift+RePág no se consideran resueltos por ese resultado. El buffer de xterm
y el historial del panel de tmux son distintos.

El QR TOTP pertenece al alta de la cuenta que utiliza el segundo factor. La
plataforma TEC 6.4 ya contempla TOTP; mostrar el QR es una mejora pendiente.
No se introduce como requisito que el cliente tenga que dar de alta un TOTP
para poder pedir ayuda. La cuenta técnica, el consentimiento local y las claves
de API son elementos distintos.

## Dos aplicaciones de selección

1. Gestor del catálogo: crawler, `light-url.txt`, `heavy-url.txt`, procedencia,
   verificación y recetas de arranque. Selección de distribuciones, arquitecturas,
   formatos y herramientas de todo el catálogo admitido.
2. Selector de la edición instalada: perfiles de paquetes estilo tasksel,
   traducidos a los nombres y formatos de Fedora y Debian.

La comparación con Kali describe la amplitud de la suite forense. No implica
que las imágenes Fedora y Debian pasen a ser derivados oficiales de Kali ni
autoriza a mezclar sus repositorios.

## Catálogo, PXE y actualizaciones

El catálogo conserva las URL originales y puede ofrecerlas en AUX y TEC. El
crawler consulta fuentes conocidas con frecuencia moderada, caché y peticiones
condicionales. Guarda la ruta interna y la ruta publicada de kernel, initrd y
SquashFS cuando exista. Una respuesta HTTP satisfactoria no prueba un arranque.

Excalibur ejecutará la actualización los sábados a las 03:00. La zona horaria
está pendiente de confirmar; la plantilla usa UTC como propuesta explícita.
El servicio todavía no está instalado por esta entrega. La anterior imagen
comprobada se conserva cuando se publica una nueva.

## Entrada en instalaciones

AUX Assist ofrecerá detección de sistemas, elección del destino, desbloqueo
cuando corresponda, preparación de montajes y entrada mediante chroot. Habrá
inspección y reparación, con identificación visible del sistema de destino.
La implementación aún no está incluida. No se promete compatibilidad universal:
arquitectura, sistemas de archivos y estado de la instalación limitan el acceso.

## Puntos que siguen abiertos

- Rama exacta de Fedora y lista definitiva de paquetes disponibles.
- Disposición y capacidad de la llave; nombres finales de sus imágenes completas.
- Soporte BIOS, UEFI y Secure Boot comprobado por cada artefacto.
- Custodia y coste de claves GPT/Gemini y política de sesiones persistentes.
- Zona horaria del trabajo semanal y publicación automática tras las comprobaciones.
- Portar AUX Assist 6.4 al sistema estándar y completar las nuevas interfaces.

