# Perfil Alpine

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
Author & Credits: https://www.alawise.es/1-s

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
