# ./aux 8.0.0-beta.5 — ISO, asistencia y despliegue

Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
Author & Credits: https://www.alawise.es/1-s

Suite de herramientas para preparar medios, asistir equipos y publicar
réplicas netboot. Consola: `python3 aux`. Ayuda: F1 en los diálogos y
`--help` en cada aplicación. Python 3.12 o posterior; consola de al menos
80 columnas por 16 filas para los diálogos compartidos.

Primera beta de fuentes de la serie 8, basada en la suite completa 7.0.1-beta.4.
Python 3.12 o posterior para los filtros de extracción seguros. No incorpora
ISO nuevas de distribuciones ni una Rescue compilada en esta edición.

## Catálogo único y estado observado

| Archivo | Responsabilidad |
| --- | --- |
| `fast-boot.json` | Rutas, accesos, presupuestos y parámetros preestablecidos. |
| `catalog.json` | Recursos, versiones, orígenes, componentes y política CDE editable. |
| `state/status.json` | Observaciones generadas por checkstatus y evidencias de prueba. |

La palabra RASCDE tiene 24 bits, cuatro reservados. CDE indica la política;
A y S describen observaciones. Las listas url/light/heavy dejan de ser fuentes
activas: sus datos históricos solo se conservan como fixtures de regresión.
La semilla consolida 211 referencias. Sus metadatos importados no equivalen a
una comprobación actual de disponibilidad.

```bash
./aux catalog validate
./aux catalog --interactive
./aux catalog refresh --resource ID --apply
./aux checkstatus
./aux download --resource ID --dry-run
./aux download --resource ID --apply
./aux deploy --resource ID --dry-run
./aux deploy --resource ID --apply
./aux checkstatus
./aux generate --apply
```

Los ID se obtienen con `./aux catalog show`. Las rutas relativas se interpretan
junto a la configuración utilizada: trasladar también sus archivos referenciados
o utilizar rutas absolutas. Los planes no escriben ni descargan; `--apply`
ejecuta cada fase por separado. La descarga sin destino mantiene caché; el destino
sin descarga exige una fuente existente. No se borran archivos ajenos ni versiones
anteriores. Caché y publicación separan artefactos distintos con el mismo nombre.

`./aux-checkstatus` también funciona por separado. `--dry-run` muestra su alcance,
`--json` imprime el informe, `--show` consulta el guardado, `--resource ID` filtra
la presentación, `--hash` contrasta bytes locales y `--origin` consulta cabeceras
de los orígenes. «Comprobada» exige una prueba real de arranque hasta login;
`checkstatus --record-test` registra una atestación del operador y el hash de su
log privado. No deduce ese resultado de un archivo presente o un checksum.

El inventario de Bastion se obtiene previamente por rsync o FTP/FTPS. Configurar
`checkstatus.bastion.enabled`, transporte y pares directorio/URL pública. Se
entrega desactivado porque faltan los accesos del servidor. Su presupuesto se
deriva del SSD; sus políticas pueden ser distintas. El listado no descarga ISO.
`generate` consume la instantánea y no consulta Bastion durante esa fase.

Los presets Alpine/Fedora/Debian son acumulables y comparten los recursos chroot
establecidos. Gentoo stage3 se entrega como manifiesto oficial resoluble, sin
inventar versión o checksum. El editor web exporta un único `catalog.json` y
conserva decisiones manuales. Las propuestas GPT/Gemini tienen Max tokens editable
y requieren revisión antes de guardarse en el catálogo.

Se ofrecen instaladores ligeros ampliables mediante mirrors y componentes con
origen exacto para construir desde cero. Las recetas aprobadas por componentes
generan `components.ipxe`; su existencia no acredita la prueba hasta login.
Rescue incorpora `dialog` y una alternativa de consola serie. TEC incluye los
tres foros moderados con enlaces desde las páginas de usuario.

## Edición 8: documentación

- [Bits y datos](docs/SCHEMA-8.md)
- [Manual de operación](docs/OPERATIONS-8.md)
- [Mapa de navegación y diagramas](docs/NAVIGATION-8.md)
- [CDN: preparación del piloto](docs/CDN-8.md)
- [Checklist de entrega](docs/CHECKLIST-8.md)
- [Pruebas de esta beta](docs/TESTING-8.md)

El presupuesto se comprueba sobre las fuentes extraídas: máximo 28.000.000 bytes,
excluyendo estado de ejecución, cachés y el propio manifiesto. `SHA256SUMS`
identifica cada archivo entregado. La instalación sobre equipos reales, los
arranques BIOS/UEFI y la activación CDN conservan su validación independiente.

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

La beta.2 incorpora identidad de destino, libro de recetas AUX, auditoría HTTP, estado web con 20 bits y adaptación experimental GPT/Gemini. Uso y límites: [BETA2-8.md](docs/BETA2-8.md).

Beta.3: catálogo ampliado a 283 registros, self-assamblers en `self-assamble/` y despliegue en matrioshka. Presupuesto de fuentes: 24 MB; envoltorio contabilizado aparte. Guía: [BETA3-8.md](docs/BETA3-8.md).

Beta.4 corrige la búsqueda de `catalog.sources.json` con configuraciones personales antiguas. Uso y recuperación: [BETA4-8.md](docs/BETA4-8.md).

Beta.5 corrige las descargas con metadatos caducados, fija Gentoo a directorios fechados y verifica las firmas oficiales de Arch. Guía: [BETA5-8.md](docs/BETA5-8.md).
