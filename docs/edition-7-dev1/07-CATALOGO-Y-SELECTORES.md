# Catálogo, crawler y los dos selectores

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Aplicación de catálogo

El crawler mantiene un catálogo normalizado y genera `light-url.txt` y
`heavy-url.txt`. Son clases de descargas, no nombres de servidores. El formato
heredado es una URL por línea, admitiendo comentarios `#`. Los originales 6.4
se conservan en la referencia y no se presentan como enlaces actualizados.

El selector permite explorar distribución, versión, arquitectura, formato y
herramientas; selecciona descargas y recetas. El catálogo debe poder ampliarse
a nuevas familias sin afirmar que cada formato arranca en cada arquitectura.
No se fija un umbral de megabytes inventado para cambiar automáticamente la
clasificación light/heavy: se conserva explícitamente en cada entrada.

Cada fuente tiene su adaptador: metadatos o índices oficiales antes que HTML
frágil; HTML cuando sea necesario y con un parser revisable. Usar frecuencia
moderada, identificación del cliente y caché HTTP. No sortear bloqueos ni
probar directorios arbitrarios de servidores desconocidos.

`config/catalog.example.json` muestra los campos previstos. Es un ejemplo de
datos, no el crawler implementado. En producción deben rellenarse URL, hashes,
rutas y pruebas reales; no publicar marcadores como si fueran recetas válidas.

## Pipeline previsto

1. Consultar fuentes conocidas y detectar candidatos nuevos.
2. Registrar versión y arquitectura; descartar descargas incompletas o HTML.
3. Descargar a un área temporal y verificar firma/suma según la política de fuente.
4. Inspeccionar el contenido cuando sea necesario y formar la receta.
5. Desplegar a una ruta versionada y comprobar las URL públicas reales.
6. Registrar pruebas BIOS/UEFI aparte de la comprobación de HTTP.
7. Publicar catálogo, listas, páginas y menú de forma coherente.

El `latest` del proveedor se resuelve a una composición identificable; el catálogo
no mezcla kernel de ayer con initrd o SquashFS de hoy. Conservar la anterior
versión comprobada. La actualización de los enlaces de descarga no basta para
declarar compatible un arranque PXE.

AUX y TEC pueden ofrecer tanto la URL original del fabricante como una copia
local cuando exista. Mostrar fuente, versión, tamaño, hash y estado de arranque.
Las herramientas de administración o doble uso conservan procedencia y función
visibles; su ubicación en áreas avanzadas puede depender de permisos, sin
camuflar archivos o sus nombres.

## Aplicación de perfiles de instalación

Este segundo selector elige la composición de nuestra suite. Trabaja con roles
comunes y adaptadores de paquetes Fedora/Debian. Ejemplos de roles son kernel y
firmware, escritorio, discos y adquisición, recuperación, red, administración,
asistencia humana y asistencia API.

La salida será un manifiesto de selección y los archivos específicos del
instalador. Se verifican dependencias y paquetes disponibles antes de producir
Kickstart o preseed. Si una herramienta falta en una distribución se indica;
no se selecciona un repositorio ajeno automáticamente. La selección inicial
incluida es manual y no representa el menú tasksel nuevo ya implementado.

## Consultas GPT y Gemini

El asistente puede leer documentación oficial aportada como datos y proponer
campos de receta estructurados. Debe aportar las fuentes, la versión a la que
se refiere y lo que no pudo confirmar. El programa valida esquema, rutas y
descargas; la propuesta no se publica ni se ejecuta como shell por el mero
hecho de haber sido generada por un modelo.

Para OpenAI, revisar la API Responses y sus salidas estructuradas. Mantener la
clave en el backend y modelos, límite de salida y presupuesto configurables.
Reutilizar resultados por versión para evitar consultas repetidas en cada
comprobación HTTP. Gemini tendrá su adaptador separado con el mismo contrato
de datos. Esta edición no contiene credenciales ni hace llamadas de pago.

Los textos de páginas descargadas y de documentación se consideran datos de
entrada, no órdenes para el proceso con permisos de publicación.

