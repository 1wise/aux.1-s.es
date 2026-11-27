# Configuración central

Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
Author & Credits: https://www.alawise.es/1-s

Abrir `python3 aux-config --interactive`. La ayuda de cada campo explica su
significado, ejemplo y límites. Los valores inválidos se corrigen en el campo.
Los ajustes de usuario se guardan fuera de las fuentes para conservar sus sumas.

`output` es la raíz pública; `cache` conserva las descargas fuera de ella;
`ram_dir` señala el tmpfs. Las rutas INPUT de una réplica se inspeccionan sin
convertirlas en su OUTPUT de trabajo. Elegir directorios distintos y comprobar
permisos y espacio antes de ejecutar.

`base_url` identifica AUX, `pxe_url` entrega el arranque y `download_url` ofrece
las descargas completas. Elegir Excalibur o Bastion cambia el perfil de URL;
la tarea sigue ejecutándose en el equipo desde el que se abre la consola.

Configurar `mirror.transport` como rsync o ftps. SSH usa host, usuario, puerto,
identidad y raíz remota. FTPS utiliza los campos ftp_host, ftp_user, ftp_port,
ftp_root y ftp_tls. La contraseña nunca se introduce en un campo público.

Los presupuestos miden archivos. Descontar la reserva RAM y prever expansión,
sistema operativo y contenido ya cargado. El plan consulta el espacio real.

Las claves GPT/Gemini y FTPS pertenecen al almacén privado de AUX: carpeta 0700
y archivo 0600, fuera de fuentes, caché y web. osctrl recibe su token desde
OSCTRL_API_TOKEN, el almacén privado o una entrada temporal oculta; no se guarda en fast-boot.json.
