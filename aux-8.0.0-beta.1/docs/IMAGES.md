# ISO y perfiles de instalación

Timestamp: 2026-11-22 | Version: 8.0.0-beta.1
Author & Credits: https://www.alawise.es/1-s

Abrir `python3 aux-images --interactive`. Las opciones preparan un instalador
ISO oficial personalizado, perfiles Kickstart/preseed, una receta Live, una
construcción Live en VM KVM o un archivo de imagen USB. Revisar el plan de cada
generador; no confundir la receta con una ISO ya compilada.

El medio de entrada debe ser un archivo existente. El campo SHA-256 requiere
64 cifras hexadecimales y se contrasta con los bytes. La fuente de confianza
es el proveedor; una suma local no sustituye la comprobación de su firma.
Elegir una salida nueva, fuera de /dev y con directorio padre disponible.

Los perfiles Debian/Fedora conservan tareas y grupos nativos y añaden los
componentes AUX seleccionados. El constructor debe comprobar los paquetes en
repositorios compatibles con su rama. No se garantiza que una receta o un
perfil de otra arquitectura pueda ejecutarse sobre el constructor actual.

El generador USB crea un archivo. No graba un dispositivo físico. La capacidad
se expresa en bytes positivos múltiplos de 512. GENERAR confirma el plan;
Esc cancela. Los errores de capacidad, rutas y sumas se corrigen sin abandonar
el campo.

La aceptación requiere construir en el entorno adecuado, verificar hashes y
probar los medios con la arquitectura y firmware de destino. Secure Boot
requiere una cadena firmada y de confianza; el cliente iPXE incluido no
acredita por sí mismo esa compatibilidad.

## Ubicación de las llaves propias

La preparación de nuestras llaves USB/SSD y su entorno Live se organiza en ASSISTANCE.md, dentro de Asistencia. El selector general de generadores conserva el acceso a las herramientas existentes.

## Alpine Linux · edge / x86_64

Alpine está disponible en el selector web y en `aux-setup --interactive`.
`aux-profile --distro alpine --output /tmp/aux-alpine` genera selection.json,
packages.txt, world, repositories y apply-alpine.sh. La ejecución sin --apply
muestra la ayuda y termina. El perfil se aplica dentro del Alpine de destino
con `sh apply-alpine.sh --apply`, conservando sus repositorios configurados.

La raíz nueva usa apk --root --initdb y requiere un constructor con apk y
claves oficiales de confianza en /etc/apk/keys. Las comprobaciones de firmas
siguen activas. No se configura el cargador ni se particiona el disco.
La ISO conserva setup-alpine y añade /aux/profile/apply-alpine.sh para aplicar
explícitamente después de la instalación; no es una instalación desatendida.
Antes de modificar paquetes, el perfil ISO comprueba el marcador del medio
y las sumas de las fuentes incorporadas.

Alpine usa OpenRC: AUX instala el cliente de asistencia para ejecución manual,
sin las unidades systemd de Debian/Fedora. Los servicios AI y el temporizador
del catálogo requieren integración OpenRC adicional. La generación de planes
y perfiles se comprueba automáticamente; el arranque BIOS/UEFI y la instalación
física de esta variante siguen pendientes de prueba.
