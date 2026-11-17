# Manual de consola AUX

Timestamp: 2026-11-17 | Version: 7.0.1-beta.3
Author & Credits: https://www.alawise.es/1-s

## Navegación y acciones

`aux` presenta ISO, asistencia y despliegue en ese orden. Cada aplicación
conserva su CLI; --help explica sus argumentos. F1 abre una ayuda desplazable
sin perder casillas, posición, valores ni el plan. Enter o Esc cierra la ayuda
y regresa al diálogo. Esc en el diálogo cancela; una palabra incorrecta no
cancela ni ejecuta. En terminal de texto, ?ayuda muestra ayuda y :cancelar
cancela un campo; los menús numéricos aceptan ? y 0.

Flechas mueven; espacio marca; Tab cambia de panel; / busca; Retroceso vuelve
de un grupo; S conserva la selección. Ctrl+U limpia el campo. Un número o una
casilla inválidos se corrigen sin cambiar la selección anterior. El menú
muestra la aplicación, versión y si configura o ejecuta.

## Campos de configuración

### observe.api_url

Origen HTTPS del servicio osctrl-api, sin credenciales. Puede incluir /api/v1. El token se mantiene en el almacén privado o OSCTRL_API_TOKEN.

### observe.environment

Nombre o UUID del entorno osctrl seleccionado. Debe proceder del servicio; no se deduce de un hostname.

### observe.limit

Máximo de filas de observación: 1 a 1000. Valor inicial: 100. Los resultados de consultas remotas se paginan.

### observe.ca_file

CA PEM de confianza para una API con certificado privado. Vacío usa las autoridades del sistema. No desactiva la validación TLS.

### URL HTTPS de la API osctrl

Origen HTTPS de osctrl-api, sin token ni credenciales en la URL. Ejemplo: https://osctrl.example.org. Se valida el certificado.

### Identificador del entorno osctrl

Nombre o UUID devuelto por osctrl para el entorno autorizado. Se conserva al cambiar de consulta.

### Identificador de la consulta osctrl

Nombre de una consulta existente en el entorno elegido. Se leen sus resultados; no se crea ni lanza una consulta nueva.

### Servidor TLS osctrl: hostname[:puerto]

Servidor de enrolamiento osctrl-tls, separado de la API de operadores. Copiar hostname y puerto del entorno, sin protocolo ni ruta.

### JSON local de los cinco endpoints TLS

Archivo JSON con las cinco rutas TLS del entorno. No incluye secreto ni comandos.

### Archivo CA PEM existente

Archivo local con la autoridad de confianza PEM del servidor TLS. Debe existir y corresponder al entorno de enrolamiento.

### Ruta privada del secreto de enrolamiento

Ruta absoluta del archivo privado que leerá osqueryd. AUX no lee ni copia el secreto.

### Directorio nuevo privado para enrolamiento

Carpeta nueva fuera del código y la web, con padre existente. Se crean flags 0600 dentro de una carpeta 0700; el servicio no se activa.

### output

Raíz pública de salida: índices web y archivos preparados. Ejemplo: /var/www/aux.1-s.es/html. No es la caché de descargas.

### cache

Caché persistente de descargas, fuera de output. Ejemplo: /var/www/aux.1-s.es/isos. Conservarla evita descargar de nuevo.

### ram_dir

Directorio de trabajo sobre tmpfs. Ejemplo: /dev/shm/aux-pxe. El presupuesto debe incluir archivos, extracción y RAM del sistema.

### catalog_file

Archivo JSON del catálogo de origen. Elegir el catálogo publicado por el último rastreo válido.

### catalog_profile

Perfil JSON revisado de esta réplica: selección, límites y recetas aprobadas. Puede quedar vacío si no se usa un perfil.

### checksums

Archivo SHA256SUMS de confianza para contrastar descargas. Una suma calculada localmente no acredita la firma del proveedor.

### url_file

Lista de descargas completa: una URL por línea; # introduce un comentario. No inicia la descarga al elegirla.

### light_url_file

Lista Light para medios elegidos para RAM. Light describe una selección; no garantiza espacio para su extracción.

### heavy_url_file

Lista Heavy para imágenes que se conservarán en disco. Revisar espacio libre y tamaño de las imágenes.

### base_url

URL HTTP(S) del portal gráfico AUX, sin credenciales. Ejemplo: https://aux.1-s.es.

### pxe_url

URL del servidor que entrega menu.ipxe, kernel e initrd. Debe ser accesible desde el cliente que arranca.

### download_url

URL del espejo para descargas completas. Ejemplo: https://b.1-s.es. No cambia por sí sola el contenido del espejo.

### only

Filtro de recursos de esta tarea. Vacío incluye todos los recursos de la selección actual; no borra otros archivos.

### jobs

Descargas simultáneas, de 1 a 16. Reducir en enlaces lentos o almacenamiento limitado. Ejemplo: 4.

### ftp_host

Nombre del servidor FTPS, sin https://, usuario ni puerto. Ejemplo: ftp.example.org.

### ftp_user

Cuenta FTPS del alojamiento. La contraseña se solicita oculta o procede del almacén privado.

### ftp_port

Puerto del servicio FTPS explícito, entre 1 y 65535. Habitualmente 21; confirmar el del alojamiento.

### ftp_root

Raíz remota de la réplica. Revisar el directorio exacto del alojamiento; evitar / y recorridos con ..

### ftp_tls

true mantiene FTPS con validación del certificado. false utiliza FTP sin cifrado; elegir sólo si el servicio lo exige.

### mirror.transport

Transporte de réplica: rsync sobre SSH o ftps explícito. El contenido público se replica íntegro.

### mirror.source_root

Raíz INPUT pública ya preparada. Se inspecciona antes de producir OUTPUT; no debe confundirse con la carpeta de trabajo.

### mirror.state_root

Directorio privado para inventarios, planes y estados de publicación. Debe quedar fuera de la raíz web.

### mirror.release_id

Identificador de esta publicación. Letras, cifras, punto, guion y subrayado; ejemplo: aux-current.

### mirror.minimum_isos

Cantidad mínima de ISO exigida al inventario antes de transferir. Ajustar al catálogo real de la réplica.

### mirror.remote_root

Directorio remoto absoluto destinado a la réplica, distinto de /. No permite .. ni reemplaza el servicio remoto.

### mirror.ssh_host

Servidor SSH de la réplica, sin protocolo ni usuario. Se utiliza rsync sobre SSH.

### mirror.ssh_user

Cuenta SSH autorizada para publicar dentro de la raíz remota seleccionada.

### mirror.ssh_port

Puerto SSH entre 1 y 65535. Ejemplo: 22.

### mirror.ssh_identity

Ruta local de la clave privada SSH. Mantenerla fuera de código, caché y raíces públicas.

### ram_budget_gib

Límite de RAM nominal en GiB para archivos. Se aplica la reserva; el sistema arrancado necesita memoria adicional.

### ssd_budget_gib

Límite de almacenamiento persistente en GiB. También cuentan las copias Light conservadas en disco.

### ram_reserve_percent

Porcentaje de RAM reservado al sistema, de 0 a 99. Ejemplo: 10 reserva el diez por ciento.

### ai.enabled

Activa las propuestas de IA. Cada consulta sigue requiriendo revisión del contenido y confirmación de envío.

### ai.openai.model

Identificador del modelo disponible en la cuenta OpenAI. No introducir una clave API aquí.

### ai.gemini.model

Identificador del modelo disponible en la cuenta Gemini. No introducir una clave API aquí.

### tec.public_url

URL pública de asistencia TEC. AUX y PXE pueden funcionar sin instalar TEC.

### tec.data_dir

Estado privado de asistencia: sesiones y registros. Debe quedar fuera de la raíz web.

### tec.web_dir

Directorio del servicio web TEC, que requiere su propio servidor y configuración.

### tls.certificate

Ruta del certificado público PEM del servicio. Comprobar nombre y cadena de confianza.

### tls.key

Ruta de la clave privada TLS. No copiarla a descargas ni al portal.

## Consultas de IA

La petición inicial es editable:

> Proponer una selección netboot y rescate para las arquitecturas del catálogo, respetando los límites RAM/SSD y los modos actuales. Indicar URL oficial, versión, tamaño conocido, checksum del proveedor y archivos kernel/initrd requeridos. Separar evidencias de hipótesis; no ejecutar órdenes ni aprobar recetas.

El plan explica los datos enviados y el proveedor. CONSULTAR confirma el envío; las propuestas requieren revisión y cada receta se aprueba por separado.

## Comandos

```bash
python3 aux
python3 aux-config -i
python3 aux-images -i
python3 aux-enter -i
python3 aux-observe -i
python3 aux-catalog -i
python3 aux-release -i
bash download.sh --dry-run
bash deploy.sh disk --dry-run
bash generate.sh --dry-run
```
