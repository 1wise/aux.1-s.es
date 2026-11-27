# Identidad, productos y adaptación experimental

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
Author & Credits: https://www.alawise.es/1-s

## Identidad del equipo de destino

El instalador web, los perfiles CLI y el configurador interactivo permiten hostname, locale, timezone y usuario. La selección es opcional. El hostname debe ser único y estable por equipo; clonar el mismo nombre en varias máquinas produce colisiones. Las contraseñas no se guardan en el JSON. Debian las solicita en el instalador; las cuentas preparadas en Fedora, Alpine o un árbol raíz quedan bloqueadas hasta definir una contraseña localmente. Se conservan las cuentas personales existentes sin modificar sus contraseñas.

Ejemplo de preparación, sin modificar el sistema actual:

```sh
./aux-profile --help
./aux-setup --help
./aux-observe enrollment --help
```

El enrolamiento nuevo propone `--host_identifier=hostname`; UUID e instance siguen disponibles. Esta opción de osquery elige la identidad enviada al servicio: no cambia el UUID del hardware ni migra los nodos ya registrados. El selector TUI muestra las tres alternativas. Referencia: https://osquery.readthedocs.io/en/latest/installation/cli-flags/

## Tres productos mantenidos

`recipes.html` presenta el libro AUX: Debian y Fedora netboot, Alpine kernel/initrd/modloop, y el procedimiento Gentoo stage3/chroot. Los tres primeros se compilan desde el catálogo en `components.ipxe`, accesible desde `menu.ipxe`. Cada receta fija versión, arquitectura, componentes y origen oficial. La aprobación editorial permite publicarla como candidata; no acredita un arranque. Las recetas propias de perfiles anteriores se conservan en el mismo libro.

`catalogue.html` ofrece los tres presets acumulativos y las políticas CDE. `urls.html` separa los orígenes con respuesta HTTP comprobada del registro de mirrors; la presencia de cada copia requiere checkstatus. El foro tiene tres tableros, recetas PXE, políticas de despliegue y URL/mirrors. Las ampliaciones enlazan la receta de partida y pasan por moderación antes de alterar el catálogo.

```sh
./aux catalog audit
./aux catalog audit --apply
python3 -m auxlib.seed_recipes --apply
python3 -m auxlib.products --apply
```

La auditoría HTTP no descarga imágenes completas, no calcula su checksum y no prueba el arranque. Publica fechas, redirecciones, errores y discrepancias de tamaño. La revisión semanal conserva la referencia anterior cuando falla un resolver. El timer systemd incluido requiere instalación explícita; no se activa al extraer el paquete.

## Estado y edición de JSON

`status.html` usa el mismo modelo y exportador JSON del catálogo. Cada recurso tiene una fila horizontal de 20 casillas: A/S observados y C/D/E editables. El contenedor permite desplazamiento horizontal en pantallas estrechas. Info abre versión, arquitectura, tamaño, checksum, origen y observaciones. Los cuatro bits reservados permanecen en cero. Una raya representa observación desconocida; no significa ausencia.

C es un campo de cuatro bits con dos bits bajos que forman el nivel de crawl (0 a 3), más candidato PXE y resolución. D controla descarga, actualización, conservación y archivo. E propone ubicaciones simultáneas. «Archivar» implica conservación aunque su casilla individual esté desmarcada.

La exportación `catalog.json` contiene recursos y políticas. `status-public.json` es una proyección de observaciones, sin rutas privadas de evidencias. Importar checkstatus requiere una instantánea reciente del mismo artefacto; no cambia CDE. La casilla Login sólo se activa con evidencia del instalador hasta la pantalla de acceso.

## GPT / Gemini experimental

La suite puede describir sus módulos y contratos, exportar una solicitud y pedir una adaptación mediante las APIs ya soportadas. Esto es autodescripción y adaptación asistida, no consciencia. La página `adapt.html` prepara el objetivo; las claves y las consultas permanecen en la consola privada.

```sh
./aux evolve --describe
./aux evolve --goal 'Preparar un aula de sistemas' --file README.md --output solicitud.json
./aux evolve --request aux-adaptation-request.json --interactive
./aux evolve --proposal propuesta.json
./aux evolve --proposal propuesta.json --apply --output /ruta/nueva/aux-aula
```

Una consulta real requiere proveedor, modelo disponible y clave privada. Se muestran objetivo y límite de tokens antes de confirmarla. El resultado pasa por validación de esquema, hash de revisión, rutas y tamaño. Se presenta un diff y sólo se guarda en un directorio nuevo. Los originales, estado, credenciales y datos del foro no se envían ni se sobrescriben. Las comprobaciones propuestas por la IA quedan `not-run` hasta ejecutarlas. Esta entrega no ha efectuado consultas de pago ni aplicado código generado por un asistente.
