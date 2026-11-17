# ./aux — ISO, asistencia y despliegue

Timestamp: 2026-11-17 | Version: 7.0.1-beta.4
Author & Credits: https://www.alawise.es/1-s

Suite de herramientas para preparar medios, asistir equipos y publicar
réplicas netboot. Consola: `python3 aux`. Ayuda: F1 en los diálogos y
`--help` en cada aplicación. Python 3.10 o posterior; consola de al menos
80 columnas por 16 filas para los diálogos compartidos.

## ISO y medios

`aux-images` prepara instaladores, perfiles y medios. La instalación sobre el
sistema actual aparece al final de Setup y requiere un plan explícito.

## Asistencia

`aux-enter` inspecciona sistemas; `aux-assist` coordina la asistencia local;
`aux-observe` consulta osquery local y osctrl por HTTPS y prepara flags de
enrolamiento. osquery y osctrl se instalan y administran por separado.

## Despliegue

Configurar con `aux-config`, seleccionar con `aux-catalog`, descargar,
desplegar y generar. `aux-release` organiza la réplica íntegra por fases.
Cada tarea conserva su CLI y un plan de revisión.

## Documentación

- [Manual de campos y navegación](docs/MANUAL.md)
- [Configuración](docs/CONFIGURATION.md)
- [Catálogo e IA](docs/CATALOG.md)
- [ISO y USB](docs/IMAGES.md)
- [Asistencia](docs/ASSISTANCE.md)
- [osquery y osctrl](docs/OBSERVABILITY.md)
- [Réplica](docs/REPLICA.md)
- [Pruebas y límites](docs/TESTING.md)

Código y recursos de la suite, sin ISO de distribuciones ni credenciales.
La disponibilidad de orígenes y el arranque físico requieren sus propias
comprobaciones. Contenidos: CC BY-NC-SA 4.0; créditos y arquitectura en
https://www.alawise.es/1-s.

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
