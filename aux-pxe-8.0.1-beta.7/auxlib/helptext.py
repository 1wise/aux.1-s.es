# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""One source of contextual field guidance for TUI, plain terminals and manuals."""
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

GUIA = {
    'checkstatus.bastion.enabled':'Activa el rastreo remoto. Guardar FTP no lo activa por sí solo. B en el tablero reutiliza la conexión y permite revisar la raíz y su URL antes de activarlo.',
    'checkstatus.bastion.transport':'Inventario por rsync, ftps, ftp o auto. Auto usa SSH si está configurado y permite el FTP alternativo guardado.',
    'checkstatus.bastion.fallback_ftp':'Si falla rsync, usar el FTP/FTPS configurado con sus propias credenciales y raíz. Respeta ftp_tls; no desactiva TLS automáticamente.',
    'checkstatus.bastion.directories':'Lista JSON de path y public_url. Para rsync puede incluir ftp_path con la ruta equivalente en FTP. B configura estos datos desde la conexión existente; SSH y FTP pueden mostrar raíces distintas.',
    'presets.preset_ram_gib':'RAM disponible por preset en GiB. Los presets comparten recursos y usan un fondo comun sin duplicarlos. Defecto 10.',
    'presets.preset_ssd_gib':'SSD y Bastion por preset en GiB; defecto 75. El total incluye imagenes y deploys, con el limite fisico configurado.',
    'P: 1 usuario, 2 tendencia, 4 obligatorio, 8 IA para el sector':'Un hexadecimal combinable. 5 = usuario y obligatorio; A = tendencia e IA. P ordena preferencias y no activa acciones CDE ni acredita disponibilidad, integridad o login. Un obligatorio conserva su seleccion y comunica conflictos de presupuesto.',
    'status_file':'Instantanea generada por checkstatus. Conserva fecha, estado por ubicacion y evidencia; no es un catalogo editable.',
    'evidence_file':'Registro privado de pruebas reales de arranque hasta login. Un hash correcto no activa comprobada.',
    'checkstatus.max_age_seconds':'Vigencia maxima de la instantanea, en segundos. generate exige un estado del mismo catalogo y configuracion.',
    'ai.max_output_tokens':'Maximo de tokens de salida por consulta GPT/Gemini, de 128 a 4096. Se puede ajustar antes de cada llamada.',
    'Política CDE (3 hex); A/S se obtienen de checkstatus':'Tres cifras hexadecimales: C investiga, D adquiere/retiene y E propone ubicaciones. A y S son observaciones; P indica prioridad.',
    'observe.api_url': 'Origen HTTPS del servicio osctrl-api, sin credenciales. Puede incluir /api/v1. El token se mantiene en el almacén privado o OSCTRL_API_TOKEN.',
    'observe.environment': 'Nombre o UUID del entorno osctrl seleccionado. Debe proceder del servicio; no se deduce de un hostname.',
    'observe.limit': 'Máximo de filas de observación: 1 a 1000. Valor inicial: 100. Los resultados de consultas remotas se paginan.',
    'observe.ca_file': 'CA PEM de confianza para una API con certificado privado. Vacío usa las autoridades del sistema. No desactiva la validación TLS.',
    'URL HTTPS de la API osctrl': 'Origen HTTPS de osctrl-api, sin token ni credenciales en la URL. Ejemplo: https://osctrl.example.org. Se valida el certificado.',
    'Identificador del entorno osctrl': 'Nombre o UUID devuelto por osctrl para el entorno autorizado. Se conserva al cambiar de consulta.',
    'Identificador de la consulta osctrl': 'Nombre de una consulta existente en el entorno elegido. Se leen sus resultados; no se crea ni lanza una consulta nueva.',
    'Servidor TLS osctrl: hostname[:puerto]': 'Servidor de enrolamiento osctrl-tls, separado de la API de operadores. Copiar hostname y puerto del entorno, sin protocolo ni ruta.',
    'JSON local de los cinco endpoints TLS': 'Archivo JSON con las cinco rutas TLS del entorno. No incluye secreto ni comandos.',
    'Archivo CA PEM existente': 'Archivo local con la autoridad de confianza PEM del servidor TLS. Debe existir y corresponder al entorno de enrolamiento.',
    'Ruta privada del secreto de enrolamiento': 'Ruta absoluta del archivo privado que leerá osqueryd. AUX no lee ni copia el secreto.',
    'Directorio nuevo privado para enrolamiento': 'Carpeta nueva fuera del código y la web, con padre existente. Se crean flags 0600 dentro de una carpeta 0700; el servicio no se activa.',
    'output': 'Raíz pública de salida: índices web y archivos preparados. Ejemplo: /var/www/aux.1-s.es/html. No es la caché de descargas.',
    'cache': 'Caché persistente de descargas, fuera de output. Ejemplo: /var/www/aux.1-s.es/isos. Conservarla evita descargar de nuevo.',
    'ram_dir': 'Directorio de trabajo sobre tmpfs. Ejemplo: /dev/shm/aux-pxe. El presupuesto debe incluir archivos, extracción y RAM del sistema.',
    'catalog_file': 'Archivo JSON del catálogo de origen. Elegir el catálogo publicado por el último rastreo válido.',
    'catalog_sources_file': 'Reglas para resolver versiones, índices y checksums oficiales. La ruta predeterminada config/catalog.sources.json usa el archivo incluido en la suite cuando no hay una copia local; una ruta personalizada se conserva y debe existir.',
    'catalog_profile': 'Perfil JSON revisado de esta réplica: selección, límites y recetas aprobadas. Puede quedar vacío si no se usa un perfil.',
    'checksums': 'Archivo SHA256SUMS de confianza para contrastar descargas. Una suma calculada localmente no acredita la firma del proveedor.',
    'url_file': 'Lista de descargas completa: una URL por línea; # introduce un comentario. No inicia la descarga al elegirla.',
    'light_url_file': 'Lista Light para medios elegidos para RAM. Light describe una selección; no garantiza espacio para su extracción.',
    'heavy_url_file': 'Lista Heavy para imágenes que se conservarán en disco. Revisar espacio libre y tamaño de las imágenes.',
    'base_url': 'URL HTTP(S) del portal gráfico AUX, sin credenciales. Ejemplo: https://aux.1-s.es.',
    'pxe_url': 'URL del servidor que entrega menu.ipxe, kernel e initrd. Debe ser accesible desde el cliente que arranca.',
    'download_url': 'URL del espejo para descargas completas. Ejemplo: https://b.1-s.es. No cambia por sí sola el contenido del espejo.',
    'only': 'Filtro de recursos de esta tarea. Vacío incluye todos los recursos de la selección actual; no borra otros archivos.',
    'jobs': 'Descargas simultáneas, de 1 a 16. Reducir en enlaces lentos o almacenamiento limitado. Ejemplo: 4.',
    'ftp_host': 'Nombre del servidor FTPS, sin https://, usuario ni puerto. Ejemplo: ftp.example.org.',
    'ftp_user': 'Cuenta FTPS del alojamiento. La contraseña se solicita oculta o procede del almacén privado.',
    'ftp_port': 'Puerto del servicio FTPS explícito, entre 1 y 65535. Habitualmente 21; confirmar el del alojamiento.',
    'ftp_root': 'Raíz remota de la réplica. Revisar el directorio exacto del alojamiento; evitar / y recorridos con ..',
    'ftp_tls': 'true mantiene FTPS con validación del certificado. false utiliza FTP sin cifrado; elegir sólo si el servicio lo exige.',
    'mirror.transport': 'Transporte de réplica: rsync sobre SSH o ftps explícito. El contenido público se replica íntegro.',
    'mirror.source_root': 'Raíz INPUT pública ya preparada. Se inspecciona antes de producir OUTPUT; no debe confundirse con la carpeta de trabajo.',
    'mirror.state_root': 'Directorio privado para inventarios, planes y estados de publicación. Debe quedar fuera de la raíz web.',
    'mirror.release_id': 'Identificador de esta publicación. Letras, cifras, punto, guion y subrayado; ejemplo: aux-current.',
    'mirror.minimum_isos': 'Cantidad mínima de ISO exigida al inventario antes de transferir. Ajustar al catálogo real de la réplica.',
    'mirror.remote_root': 'Directorio remoto absoluto destinado a la réplica, distinto de /. No permite .. ni reemplaza el servicio remoto.',
    'mirror.ssh_host': 'Servidor SSH de la réplica, sin protocolo ni usuario. Se utiliza rsync sobre SSH.',
    'mirror.ssh_user': 'Cuenta SSH autorizada para publicar dentro de la raíz remota seleccionada.',
    'mirror.ssh_port': 'Puerto SSH entre 1 y 65535. Ejemplo: 22.',
    'mirror.ssh_identity': 'Ruta local de la clave privada SSH. Mantenerla fuera de código, caché y raíces públicas.',
    'mirror.ssh_auth':'password usa ssh_password del almacén privado o solicita entrada oculta en terminal. auto usa la contraseña guardada si existe; key usa claves/agente. La huella del servidor debe estar validada en known_hosts.',
    'mirror.ssh_known_hosts':'Archivo known_hosts opcional. Vacío utiliza el de SSH del usuario actual. No se omite la validación de la identidad del servidor.',
    'ssh_password':'Contraseña SSH/rsync independiente de la de FTP. Entrada oculta en B → Contraseña SSH / rsync; se guarda en el almacén privado 0600, fuera del código y de la web.',
    'ram_budget_gib': 'Límite de RAM nominal en GiB para archivos. Se aplica la reserva; el sistema arrancado necesita memoria adicional.',
    'ssd_budget_gib': 'Límite de almacenamiento persistente en GiB. También cuentan las copias Light conservadas en disco.',
    'ram_reserve_percent': 'Porcentaje de RAM reservado al sistema, de 0 a 99. Ejemplo: 10 reserva el diez por ciento.',
    'ai.enabled': 'Activa las propuestas de IA. Cada consulta sigue requiriendo revisión del contenido y confirmación de envío.',
    'ai.openai.model': 'Identificador del modelo disponible en la cuenta OpenAI. No introducir una clave API aquí.',
    'ai.gemini.model': 'Identificador del modelo disponible en la cuenta Gemini. No introducir una clave API aquí.',
    'tec.public_url': 'URL pública de asistencia TEC. AUX y PXE pueden funcionar sin instalar TEC.',
    'tec.data_dir': 'Estado privado de asistencia: sesiones y registros. Debe quedar fuera de la raíz web.',
    'tec.web_dir': 'Directorio del servicio web TEC, que requiere su propio servidor y configuración.',
    'tls.certificate': 'Ruta del certificado público PEM del servicio. Comprobar nombre y cadena de confianza.',
    'tls.key': 'Ruta de la clave privada TLS. No copiarla a descargas ni al portal.',
}

PROMPT = ('Proponer una selección netboot y rescate para las arquitecturas del catálogo, '
    'respetando los límites RAM/SSD y los modos actuales. Indicar URL oficial, versión, '
    'tamaño conocido, checksum del proveedor y archivos kernel/initrd requeridos. '
    'Separar evidencias de hipótesis; no ejecutar órdenes ni aprobar recetas.')


def descripcion(titulo):
    if titulo in GUIA:
        return GUIA[titulo]
    if titulo.startswith('targets.'):
        return 'Perfil de URL para el destino elegido. ' + GUIA.get(titulo.rsplit('.', 1)[-1], 'Usar la URL pública del servicio, sin credenciales.')
    if titulo.startswith('bastion.'):
        return 'Nombres de dominio del alojamiento separados por comas, sin protocolo ni rutas. Ejemplo: b.example.org,b.example.net.'
    txt = titulo.casefold()
    if 'archivo ca pem existente' in txt:
        return 'Autoridad de confianza PEM del servidor TLS. Elegir un archivo existente y revisar que corresponda al entorno.'
    if 'escribir' in txt:
        return 'Revisar el plan y escribir la palabra solicitada exactamente. Una entrada incorrecta conserva el campo y el plan. Esc cancela sin ejecutar.'
    if 'sha-256' in txt:
        return 'Suma SHA-256 de 64 cifras hexadecimales obtenida de una fuente de confianza. Se contrasta con los bytes del medio.'
    if 'objetivo' in txt or 'prompt' in txt:
        return 'Petición enviada al proveedor seleccionado junto con los datos indicados en el plan. Se propone un texto editable; describir uso, arquitecturas y límites.'
    if 'modelo api' in txt:
        return 'Identificador del modelo habilitado en la cuenta del proveedor elegido. Se valida el formato; la API confirma su disponibilidad.'
    if 'presupuesto' in txt or 'reserva ram' in txt:
        return 'Cantidad en GiB, o porcentaje cuando aparece %. Se admiten decimales con punto. La extracción y la RAM de ejecución se presupuestan aparte.'
    if 'capacidad' in txt:
        return 'Capacidad del archivo de imagen en bytes, positiva y múltiplo de 512. No representa una autorización para grabar un dispositivo.'
    if 'url' in txt or 'página oficial' in txt:
        return 'Dirección HTTP(S) completa de la fuente o archivo, sin usuario ni contraseña. Conservar la ruta oficial; una propuesta no acredita su disponibilidad.'
    if 'iso' in txt and 'entrada' in txt:
        return 'Archivo ISO local existente. Se inspeccionará sin alterar el original; contrastar su suma con la fuente oficial.'
    if any(x in txt for x in ('directorio', 'salida', 'raíz', 'configuración de fuentes', 'caché http', 'publicación de metadatos', 'lista de url')):
        return 'Ruta local de este campo. ~ se expande al directorio personal. Si se pide una salida nueva, el destino no debe existir y su padre debe estar disponible.'
    if 'perfil' in txt:
        return 'Nombre local para identificar esta selección o réplica. Guardar un perfil conserva sus valores; activar lo elige como configuración local.'
    return 'Contexto: ' + titulo + '. Enter acepta la opción indicada; Esc cancela este diálogo. El plan muestra el efecto antes de ejecutar una acción.'


def ayuda(titulo):
    return [descripcion(titulo), '', 'F1: ayuda contextual. Flechas / AvPág: desplazar.',
        'Enter: aceptar. Ctrl+U: limpiar un campo. Esc: cerrar ayuda o cancelar el diálogo.',
        'Las entradas incorrectas no ejecutan acciones ni descartan los valores.',
        'Manual completo: docs/MANUAL.md | CLI: aux --help o aplicación --help.']


def valida(titulo, valor):
    """Reject malformed input at the field, before callers convert or apply it."""
    if any(ord(c) < 32 or ord(c) == 127 for c in valor):
        raise ValueError('No se admiten caracteres de control.')
    from .settings import CAMPOS, convierte
    if titulo in CAMPOS:
        convierte(titulo, valor)
        return
    txt = titulo.casefold()
    if titulo == 'Archivo CA PEM existente':
        if not Path(valor).expanduser().is_absolute() or not Path(valor).expanduser().is_file():
            raise ValueError('Elegir un archivo CA existente mediante una ruta absoluta.')
        return
    if titulo == 'Ruta privada del secreto de enrolamiento':
        if not Path(valor).expanduser().is_absolute():
            raise ValueError('La ruta privada del secreto debe ser absoluta.')
        from .settings import valida_privado
        valida_privado(Path(valor).expanduser())
        return
    frase = re.search(r'escribir\s+([A-ZÁÉÍÓÚ]+)', titulo, re.I)
    if frase and frase.group(1).upper() in ('APLICAR','EJECUTAR','GENERAR','GUARDAR','RASTREAR','CONSULTAR','VERIFICAR','EXPORTAR','ACTIVAR','ABRIR'):
        if valor != frase.group(1).upper():
            raise ValueError('Escribir ' + frase.group(1).upper() + ' o Esc para cancelar.')
    elif 'sha-256' in txt and not re.fullmatch(r'[a-fA-F0-9]{64}', valor):
        raise ValueError('Se necesitan exactamente 64 cifras hexadecimales.')
    elif 'presupuesto' in txt or 'reserva ram (%)' in txt:
        try:
            num = float(valor)
        except ValueError:
            raise ValueError('Introducir una cantidad numérica; ejemplo: 28 o 28.5.') from None
        if not math.isfinite(num) or not (0 <= num <= 99 if '%' in txt else 0 < num <= (1024 if 'ram' in txt else 1048576)):
            raise ValueError('Cantidad fuera de rango.')
    elif 'capacidad de la imagen en bytes' in txt:
        if not valor.isdigit() or int(valor) <= 0 or int(valor) % 512:
            raise ValueError('La capacidad debe ser positiva y múltiplo de 512.')
    elif 'modelo api' in txt:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', valor):
            raise ValueError('Introducir el identificador del modelo habilitado en la cuenta.')
    elif ('url https del archivo' in txt or 'página oficial de referencia' in txt) and valor:
        url = urlsplit(valor)
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Usar una URL HTTPS completa sin credenciales.')
    elif 'iso' in txt and 'entrada' in txt:
        if not valor or not Path(valor).expanduser().is_file():
            raise ValueError('Elegir un archivo ISO local existente.')
    elif any(x in txt for x in ('directorio nuevo','archivo nuevo','iso nueva de salida','raíz nueva absoluta')):
        pth = Path(valor).expanduser()
        if not valor or pth.exists() or pth.is_symlink() or not pth.parent.is_dir() or pth.resolve().is_relative_to('/dev'):
            raise ValueError('Elegir una ruta nueva con directorio padre existente, fuera de /dev.')
        if 'absoluta' in txt and not pth.is_absolute():
            raise ValueError('La ruta debe ser absoluta.')
        if 'enrolamiento' in txt:
            from .settings import valida_privado
            valida_privado(pth)
    elif ('nombre del perfil' in txt or 'objetivo:' in txt) and not valor:
        raise ValueError('Este campo no puede quedar vacío.')
