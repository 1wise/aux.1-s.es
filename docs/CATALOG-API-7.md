# Catálogo asistido, perfiles de réplica y recetas iPXE

Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
Author & Credits: https://www.alawise.es/1-s

Abrir `python3 aux-catalog -i`. El menú índigo añade dos acciones:

- Asistencia GPT / Gemini: catálogo y recetas iPXE.
- Guardar perfil de réplica y presupuestos: usa la selección manual, sin API.

## Presets y modos

Default sigue representando las listas AUX salvo que se active expresamente
un perfil como Default de esa réplica. Sugerido conserva la propuesta de instalación
y rescate de AUX. Custom conserva la selección manual y puede cargarse de un
perfil local entre sesiones. P permite cambiar de preset.

Cada entrada admite light, heavy u origin. Light cuenta para RAM y SSD; heavy
sólo para SSD; origin publica un enlace. Se conservan los 28 GiB de RAM, reserva
del 10% y 100 GiB de SSD como valores iniciales. Cada réplica puede elegir otros
presupuestos en el diálogo del perfil. Los tamaños desconocidos o fuera de presupuesto
se mantienen como origen. La expansión y el sistema arrancado necesitan espacio adicional.

Los perfiles no alteran los defaults distribuidos en light-url.txt/heavy-url.txt.
El perfil activo se guarda en state/catalog-profile.json, con copia de recuperación
antes de sustituirlo. state queda fuera de los paquetes de fuentes. Para compartir
una configuración se exporta el perfil portátil y se decide dónde publicarlo.

## Consulta asistida

1. Elegir presupuestos, GPT/OpenAI o Gemini y un modelo API disponible en la cuenta.
2. Describir el objetivo: distribuciones, herramientas, arquitectura, modos o arranque.
3. Revisar lo que se enviará y escribir CONSULTAR. Se envía la petición, el catálogo
   público resumido, los presupuestos y los fallos del crawler. No se envían archivos,
   entorno del servidor ni credenciales como contexto.
4. Revisar la propuesta estructurada. Los IDs existentes se seleccionan por catálogo;
   las fuentes nuevas declaran índice, adaptador, canal, un patrón simple de nombre y referencia.
   Stable excluye versiones preliminares; testing y beta conservan su canal.
5. VERIFICAR consulta índices, checksums y cabeceras. El modelo no declara como
   verificados tamaños, versiones, hashes ni pruebas de arranque. Una fuente que no
   se resuelve permanece visible como origen, con su error.
6. Revisar el plan efectivo y elegir EXPORTAR o ACTIVAR. Sólo esta revisión local
   puede aprobar una receta para incluirla en el menú.

La configuración pública está en config/catalog.assist.json. Los modelos están vacíos
para elegirlos en la cuenta; también se respetan los modelos y ai.enabled de fast-boot.json.
Se admite una llamada por consulta, con timeout y límite de salida; no hay reintentos
ni cambio de proveedor automáticos. Una respuesta truncada o inválida se descarta.

Las claves se obtienen de OPENAI_API_KEY o GEMINI_API_KEY (alternativamente
GOOGLE_API_KEY para Gemini), o se piden sin eco en la terminal. No se guardan en
JSON, perfiles, propuestas, páginas web ni paquetes. Las claves no se introducen
como argumentos de comandos ni en esta conversación. La integración usa los endpoints
oficiales y no sigue redirecciones de peticiones autenticadas.

El transporte conserva `store: false` en Responses y usa respuesta JSON con esquema
en ambos proveedores. Esto describe los campos enviados; no es una afirmación sobre
la política de retención o facturación de la cuenta del proveedor.

## Exportación y uso en otra réplica

El directorio exportado contiene:

| Archivo | Uso |
|---|---|
| aux-catalog-profile.json | Modos, límites, datos de catálogo y recetas revisadas. |
| crawler.sources.json | Fuentes/selección de ese perfil, independiente del catálogo base. |
| url.txt | Todas las imágenes elegidas para alojamiento local. |
| light-url.txt / heavy-url.txt | Selección por destino de almacenamiento. |
| origin-url.txt | Enlaces sin alojamiento local. |
| menu-custom.ipxe | Menú independiente de recetas aprobadas; vacío si ninguna se aprobó. |

Las entradas sin una regla conocida se comprueban como URL fijadas. Cuando se
eligen varias versiones de una misma edición se conservan como URL concretas,
sin sustituir una por la otra. Las descargas locales con nombres en conflicto
se rechazan para evitar colisiones en caché.

Revisar un perfil importado:

```bash
python3 aux-catalog --profile /ruta/perfil/aux-catalog-profile.json
python3 aux-catalog --profile /ruta/perfil/aux-catalog-profile.json --apply
```

Rastrear el perfil y revisar sus listas:

```bash
python3 aux-catalog --config /ruta/perfil/crawler.sources.json \
  --url-file /ruta/perfil/url.txt --output /ruta/perfil/state/catalog \
  --cache /ruta/perfil/state/http
python3 aux-catalog --config /ruta/perfil/crawler.sources.json \
  --output /ruta/perfil/state/catalog --sync-lists
```

La sincronización modifica las listas del perfil; no las del proyecto base.
Si todas las entradas son origen, no hay imágenes para descargar. La actualización
mantiene el catálogo remoto y los estados de verificación separados.

## Recetas para menu.ipxe

Una propuesta acepta datos de kernel, initrd, argumentos, arquitectura y firmware,
o un menú de netboot.xyz. No acepta scripts iPXE libres, órdenes de shell ni flags
de aprobación del modelo. Se comprueban las cabeceras de los recursos antes de
poder aprobar la receta. El menú identifica estas recetas como revisadas y con
arranque en hardware pendiente; elegir una receta requiere una acción del usuario.

Generar con un perfil explícito:

```bash
bash generate.sh --catalog-profile /ruta/perfil/aux-catalog-profile.json --dry-run
bash generate.sh -i --catalog-profile /ruta/perfil/aux-catalog-profile.json
```

Si hay perfil activo, generate lo lee de state/catalog-profile.json. Las recetas
aprobadas aparecen en Reviewed custom recipes. Los menús locales y el catálogo
en origen siguen disponibles. Ni la API ni exportar un perfil descargan imágenes
ni arrancan sistemas. Las recetas de firmware real aún necesitan pruebas BIOS/UEFI.

Probar la revisión sin API:

```bash
python3 aux-catalog --proposal config/catalog.proposal.example.json
```

El ejemplo selecciona una entrada del catálogo incluido y prepara un menú Debian
para elegir versión en el proveedor. Las verificaciones HTTP siguen siendo reales.

## Corrección del manifiesto de Kali

La delegación HTTPS ya configurada para los servidores de descarga se aplica
ahora también a la lectura del checksum declarado, de tamaño acotado. Así el
SHA256SUMS redirigido a un espejo público puede consultarse sin enumerar sus
servidores regionales. Los otros índices/API conservan su lista de hosts.
Los checksums se analizan por algoritmo y no se confunden con una imagen descargada.

## Taller de recetas de beta.6

Abrir desde la réplica que ya tiene las imágenes publicadas:

```bash
python3 aux-catalog --recipes --interactive \
  --deployed-catalog /var/www/aux.1-s.es/html/catalog.json \
  --selection aux-seleccion/aux-catalog-selection.json
```

También aparece Preparar recetas menu.ipxe / GPT · Gemini en el menú principal.
Se reutilizan la selección, los modos y los presupuestos guardados. El taller
lee el inventario público generado y localiza archivos de arranque dentro de los
árboles publicados. El contexto API contiene URL y tamaños públicos, no las rutas
privadas del servidor ni su configuración. Las consultas preparan hasta ocho
recetas por tanda, conservando las otras recetas del perfil.

Las URL HTTP sólo se comprueban como recursos locales cuando pertenecen a una
base configurada y al inventario de esa entrada. El kernel y el initrd requieren
archivos concretos; no se admiten rutas de otro medio. Las cabeceras se consultan
sin leer cuerpos ni seguir redirecciones. Las URL externas mantienen la política
HTTPS. También se verifican las dependencias URL presentes en los argumentos.

Cada receta comprobada se aprueba mediante su propia casilla. Guardar un perfil
no aprueba todas las propuestas. Generate añade las aprobadas al submenú y crea
lanzadores individuales, recipes.json y recipes.html. Los perfiles exportados
incluyen recipes.manifest.json. Las pruebas de hardware siguen pendientes.

index.html, index.php y las vistas de texto incluyen referencias de origen,
agrupadas incluso cuando la familia no figuraba en la lista original. Los menús
compatibles del proveedor ofrecen un lanzador iPXE individual. Una URL de imagen
conserva su condición de referencia hasta que exista una receta aprobada.

El diseño de la futura capa de cuentas, conversación y consumo de API está en
[RECETARIO-7.md](RECETARIO-7.md); beta.6 ofrece el registro de intercambio, no un foro dinámico.

## Verificación de proveedores

Las pruebas de API usan respuestas simuladas: no se han hecho llamadas de pago ni
se han validado modelos de una cuenta concreta. La revisión del endpoint de descubrimiento
público de Gemini confirmó responseMimeType, responseJsonSchema y maxOutputTokens.
El ensayo de red del checksum de Kali desde este entorno terminó con un error DNS;
la comprobación real en Excalibur sigue pendiente.

- [OpenAI: salidas estructuradas](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
- [Gemini: referencia de generateContent](https://ai.google.dev/api/generate-content).
- [Gemini: descripción REST pública v1beta](https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta).
