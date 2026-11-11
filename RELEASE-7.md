# AUX 7.0.0-beta.15

Timestamp: 2026-11-11 | Version: 7.0.0-beta.15  
Author & Credits: https://www.alawise.es/1-s

Entrega beta preparada como paquete completo. Las comprobaciones locales no
sustituyen el despliegue ni el arranque en los servidores de destino.

## Cambio beta.15

- La terminal ocupa el espacio restante de la ventana con paneles flexibles;
  las herramientas AUX quedan en un desplegable y se compacta la vista baja.
- Se incorpora el complemento Fit 0.11.0 para el xterm 6.0.0 ya distribuido.
  Filas y columnas se calculan con las dimensiones del renderizador, se reajustan
  al cambiar el panel, la ventana y las fuentes y se envían al PTY correspondiente.
- El historial de tmux conserva 20 000 líneas y habilita una barra a la derecha
  en cyan/indigo en versiones que admiten pane-scrollbars. Shift+PgUp/PgDn llegan
  al historial de la terminal elegida, también dentro de la pantalla alternativa.
- La receta solicita ncurses, ncurses-base y ncurses-term y comprueba clear,
  tput, reset, infocmp y las entradas linux/xterm/screen/tmux antes de finalizar.
- Las sesiones SSH directas reutilizan la misma configuración de terminales.
- La prueba real aportada de LVM lineal/ext4 pasa: selección, RO, conservación
  del LV previamente activo, activación temporal y cierre sin montajes residuales.

La comprobación visual del encaje, rueda y arrastre sigue pendiente en la Live;
el navegador local no pudo abrirse en este entorno. Véase docs/TERMINAL-7.md.
La entrega sigue conteniendo fuentes, no una ISO beta.15 ya construida.

## Cambio beta.14

- TEC requiere un nuevo código TOTP cada cuatro horas desde la última verificación.
  La actividad no amplía el plazo; solicitudes, registro y terminal usan el mismo límite.
- Los tickets firmados incluyen el vencimiento TOTP y no duran más allá de él.
- La pasarela limita ambas terminales a ese vencimiento, incluso con tráfico continuo
  o tickets renovados sin presentar un nuevo código. Se conserva el heartbeat corto.
- Los formularios muestran cuatro horas. Se mantienen el periodo TOTP de 30 segundos,
  la protección contra reutilización, la cuenta y la semilla existentes.
- Para aplicar el cambio hay que actualizar TEC y la pasarela del servidor. La Live
  conserva su medio original; esta entrega no exige reconstruir una ISO por el TOTP.

Véase docs/TOTP-7.md. La prueba real de selección y montaje LVM sigue abierta:
las capturas confirman el mismo arranque, el PV y el LV ext4 en ambas terminales.

## Cambio beta.13

- Se corrige TypeError: cannot use dict as a set element en los menús de AUX Enter.
- El selector usa identificadores de texto internos y devuelve el objeto original
  elegido. Los dispositivos y los LV conservan sus datos sin convertirse en IDs.
- Se conservan diccionarios iguales como opciones distintas, valores False/0/None,
  la opción predeterminada y la búsqueda por etiqueta.
- Se prueba el recorrido dispositivo, modo, LV y revisión con curses en una PTY
  real; el acceso a almacenamiento está sustituido durante esa prueba de interfaz.

La entrada directa por --device y --lv sigue disponible para probar la Live
beta.12 mientras se actualizan las aplicaciones. El fallo del selector ocurre
antes del montaje; un findmnt en /work no valida el montaje del LV.

## Cambio beta.12

- La Live incorpora tmux.conf en /usr/share/aux-assist, donde lo busca el cliente.
- AUX Enter permite seleccionar un PV, revisar su grupo y elegir un volumen lógico.
- Activación temporal de LV lineales/striped, restringida por UUID y PVs del grupo.
- Inspección con activación de solo lectura y confirmación de UUID y modo del mapeo.
- Se conservan los LV que ya estaban activos y se cierra únicamente el LV abierto
  por la operación. Los LV complejos siguen requiriendo activación manual.
- Se rechaza la raíz activa, un grupo incompleto o un mapeo de otro UUID.
- El plan no activa volúmenes. La reparación requiere confirmación antes de activar.

La prueba real de LVM en la Live sigue pendiente; se incluyen informes y ciclos
simulados de activación y cierre. Véase docs/ENTER-LVM-7.md.

## Cambio beta.11

- Se corrige el fallo Missing rescue utilities: links en el postinstalador Live.
- El RPM Fedora 45 contiene links2; el registro de links depende de un manual
  excluido por --excludedocs. La receta registra la alternativa sin ese manual.
- Se conserva un navegador ya operativo y sigue siendo obligatorio verificar
  las utilidades. Un paquete links2 ausente continúa siendo un error de construcción.
- Cinco pruebas cubren el registro real de la alternativa en directorios privados,
  el navegador existente, las dependencias ausentes y un registro que no funciona.
- La corrección se ejecuta dentro de la imagen y reutiliza el netinst verificado.

La ISO aún debe compilarse y probarse en el equipo constructor.

## Cambio beta.10

- Se corrige la inspección del netinst oficial: contiene .discinfo y no .treeinfo.
- El constructor admite ambos formatos y contrasta .discinfo con la etiqueta ISO.
- Se mantiene el rechazo de una versión o arquitectura distinta de Fedora 45 x86_64.
- Los errores muestran el diagnóstico real de xorriso en lugar de ocultarlo.
- El netinst descargado y verificado se reutiliza. La corrección no requiere
  iniciar la VM ni crear el directorio de construcción durante el plan.

## Cambio beta.9

- Constructor Live Fedora 45 x86_64 en VM KVM, con plan previo y salida nueva.
- La Live incorpora las siete aplicaciones AUX verificadas contra SHA256SUMS.
- Dos terminales humanas declaradas mediante aux-live.json dentro de la ISO.
- menu.ipxe selecciona automáticamente solo medios que declaren esa capacidad;
  las ISO antiguas siguen disponibles manualmente y se identifican como clientes antiguos.
- El constructor usa 8 GiB RAM y hasta cuatro CPU por defecto, raíz virtual de
  16 GiB y comprobación de 50 GiB libres. Rechaza un instalador de otra versión,
  checksum incorrecto y salida existente o dentro de las fuentes.
- Se contemplan los repositorios trasladados a /usr/share/dnf5/repos.d en Fedora 45.
- El aviso web identifica la falta de capacidad en la Live activa.

La entrega contiene fuentes, no una ISO nueva. La compilación Lorax y las pruebas
BIOS/UEFI, SELinux, red, consentimiento y ambas terminales siguen pendientes.
El manifiesto declara capacidades de las fuentes; no certifica arranque real.

## Cambio beta.8

- La imagen destacada vuelve al pie lateral de la portada en escritorio.
- En móvil se conserva en el pie del contenido, donde sigue visible al ocultar la barra lateral.
- El pie incluye «Descargar PNG original», con sus dimensiones reales: 1254 x 1254.
- La imagen abre el original en otra pestaña; la descarga usa el mismo PNG, sin recorte ni conversión.
- Las páginas de texto y las aplicaciones web incluyen también la descarga directa.
- Se conservan las marcas superiores, los metadatos sociales y el favicon.

- Norma compartida: configuración índigo; instalación/generación cyan.
- Cada aplicación de consola mantiene identidad y cabecera propias.
- --interactive usa menús, casillas y campos curses en Setup, Profile y los
  generadores Live/USB; Images proporciona un punto de entrada común.
- Debian agrupa tareas por escritorios/sistema, servicios e idiomas. Fedora
  agrupa complementos según los entornos que los declaran, sin perder selección.
- Setup mantiene ISO primero, sistema actual al final y aux-assist seleccionable.
- Revisión desplazable del plan y frase explícita antes de la ejecución.
- El catálogo mantiene sus dos paneles, presets y clasificación light/heavy/origen.
- Límites: 28 GiB RAM (10% reserva), 100 GiB SSD; tamaños desconocidos no se
  tratan como cero para admitir imágenes locales.
- La web muestra la beta y enlaza paquetes completos ZIP/TAR.GZ y SHA-256.
- download.sh, deploy.sh y generate.sh admiten -i / --interactive con fondo cyan,
  simulación real del comando y confirmación EJECUTAR antes de aplicar.
- aux-catalog incorpora F5 / Rastrear y revisión de la sincronización de listas.
  La configuración local incluida no requiere /etc/aux/catalog.json.
- Gentoo se obtiene del puntero oficial latest y su SHA-256. El enlace minimal
  se actualizó mediante el crawler, sin fijar manualmente una fecha.
- menu.ipxe ofrece el catálogo en origen, por distribución/categoría, con 102
  menús externos distintos y URL informativas para imágenes sin receta.
- Se conserva el CLI existente; los wrappers restauran la entrada del terminal
  para que curses funcione al invocarlos desde Bash.

La publicación HTML con enlaces de origen está disponible. La propuesta de crear
páginas locales de redirección automática y hacer que el crawler las preserve
sigue pendiente. Los ensayos de firmware, medios compilados y sistemas realmente
instalados se registran como pendientes; esta etiqueta beta no certifica producción.

La selección Custom se mantiene al alternar presets y se exporta al guardar.
Los perfiles activados en beta.4 y posteriores permiten recuperarla entre sesiones.
Los hashes prueban integridad del paquete; no constituyen una firma del autor.

## Cambio beta.2

- F5 cubre las 49 URL de descarga mediante 30 grupos de fuentes declarados.
- Edición, arquitectura y canal se seleccionan con reglas independientes; se
  incluyen Fedora Cloud, Debian Cloud, Alpine, Ubuntu, Kali, Arch, CentOS y las herramientas.
- Informe por descarga con errores, tamaños y disponibilidad HTTP separados de la versión.
- Se detectan URL nuevas sin regla; no se omiten. Se conservan las listas y
  current ante un rastreo incompleto. Las 49 reglas de sincronización conservan
  la clasificación light/heavy.
- Cabeceras HTTP y un fallback Range acotado no leen ni guardan cuerpos de imagen.
- Se han añadido pruebas de cobertura completa, fallos parciales, algoritmos
  de checksum distintos, selección de canal y conservación de la publicación.

## Cambio beta.3

- Las comprobaciones de imágenes de Fedora y Kali aceptan los espejos HTTPS
  públicos elegidos por sus redireccionadores, sin fijar espejos por país.
- Se mantienen las restricciones de hosts en índices/API y en fuentes sin
  delegación explícita. Se rechazan destinos privados, locales y multicast.
- Las redirecciones de imágenes conservan HEAD en lugar de convertirse en GET.
- Se registra la política de redirección y se conservan los errores DNS/TLS/HTTP
  y la comprobación de tamaño.

## Cambio beta.4

- Asistencia GPT/Gemini en aux-catalog para selección, fuentes y recetas estructuradas.
- Perfiles manuales y asistidos por réplica, con presupuestos y Default propio opcional.
- Exportación de listas, crawler independiente y recetas iPXE revisadas; soporte
  --catalog-profile en generate. Se conservan Default/Sugerido/Custom de AUX.
- Credenciales temporales fuera de perfiles/páginas; una llamada API por consulta,
  sin ejecución de órdenes ni aprobación del modelo.
- El manifiesto de Kali utiliza la delegación HTTPS declarada para la descarga.
- Ensayos con respuestas simuladas, fuentes/recetas verificadas en fixture y
  perfiles portátiles; pendientes llamadas reales a proveedores y arranque físico.

## Cambio beta.5

- Memtest normal y GRUB usan directorios distintos: mt86plus_9.00_x86_64 y
  mt86plus_9.00_x86_64.grub. Se conserva el árbol normal ya preparado.
- Se rechazan listas y cachés con destinos de extracción ambiguos antes de publicar.
- Las imágenes Fedora s390x y ppc64le mantienen su arquitectura y versión reales.
- El paquete permite actualizar únicamente src/common.py y auxlib/__init__.py
  en beta.4; no hace falta sustituir configuración, listas ni estado del servidor.
- Pruebas con ambas variantes ZIP en ambos órdenes, repetición del despliegue,
  descubrimiento por generate y conservación de árboles no gestionados.

## Cambio beta.6

- Las referencias de origen aparecen en la portada visual y en las vistas de
  texto. Funcionan sin JavaScript y conservan su URL al cambiar de mirror.
- Las familias adicionales forman parte del árbol. Los menús compatibles del
  proveedor tienen un lanzador iPXE propio; una ISO de origen no se encadena como script.
- Taller de recetas en aux-catalog --recipes: inventario del despliegue, selección
  conservada, comprobación HTTP y aprobación individual de las candidatas.
- Registro de revisiones recipes.json / recipes.html y manifiesto portátil.
  La propuesta de seguimiento multiusuario y cuotas está en docs/RECETARIO-7.md.
  El foro dinámico y los cobros no forman parte de esta entrega.

## Cambio beta.7

- Nueva imagen destacada independiente de los wordmarks AUX/PXE/TEC y del favicon.
- PNG original completo, sin recorte, en Open Graph y Twitter; dimensiones reales
  1254 x 1254 y URL absoluta según la base pública de la réplica.
- Imagen en el pie principal, a 144 px en escritorio y 112 px en móvil, con enlace
  al original. Se retira la miniatura anterior del crédito lateral.
- Los enlaces de páginas anidadas conservan la ruta correcta al recurso.
- La comprobación del acceso Live por IPv4 en Excalibur sigue pendiente de revisar
  el Host y la configuración activa de Nginx; no se cambian vhosts automáticamente.
