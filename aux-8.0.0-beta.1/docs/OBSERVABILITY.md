# osquery y osctrl

Timestamp: 2026-11-22 | Version: 8.0.0-beta.1
Author & Credits: https://www.alawise.es/1-s

`aux-observe` integra las herramientas de observación en AUX. No instala ni
inicia osqueryd automáticamente y no instala un servidor osctrl. osqueryi debe
estar instalado en el equipo que se inspecciona; funciona separado de la base
del daemon. Instalar el paquete apropiado desde https://osquery.io/downloads.

```bash
python3 aux-observe status
python3 aux-observe schema system
python3 aux-observe --limit 50 local ports
python3 aux-observe --interactive
```

La selección local ofrece identidad del equipo, sistema, proceso del agente,
puertos, procesos y paquetes RPM/Debian. Antes de cada SELECT se inspecciona
el esquema de la tabla. Las tablas disponibles dependen de plataforma y
permisos. Las consultas están predefinidas y acotadas; el módulo no acepta
SQL arbitrario, comandos de shell ni extensiones suministradas como entrada.

Para osctrl, configurar OSCTRL_API_URL con su origen HTTPS y facilitar un token
con permisos de lectura mediante OSCTRL_API_TOKEN. El menú también admite
entrada temporal oculta. También puede guardarse mediante aux-config en el almacén privado de AUX.
No pasar tokens como argumentos, URL ni JSON público.
La conexión pública se configura en observe.api_url, observe.environment,
observe.limit y observe.ca_file. La CA opcional mantiene TLS verificado.
El módulo no imprime el token ni el cuerpo de una respuesta de autenticación
fallida, no reenvía credenciales a redirecciones y mantiene verificación TLS.

```bash
python3 aux-observe environments
python3 aux-observe --environment LAB nodes
python3 aux-observe --environment LAB queries
python3 aux-observe --environment LAB --name INVENTARIO --page 1 --limit 50 results
```

Las llamadas consultan entornos, nodos activos, consultas existentes y sus
resultados paginados. No lanzan consultas distribuidas ni cambian usuarios,
etiquetas o permisos. LAB e INVENTARIO son nombres de ejemplo; seleccionar los
identificadores del despliegue real. Un resultado vacío puede corresponder a
una recogida todavía incompleta. Un fallo de conexión conserva el contexto del
menú y permite corregir la URL o las credenciales.

## Preparación de enrolamiento

Exportar del entorno osctrl las cinco rutas: enroll_tls_endpoint,
config_tls_endpoint, logger_tls_endpoint, distributed_tls_read_endpoint y
distributed_tls_write_endpoint. Guardarlas en un JSON local con esas cinco
claves. No deducir las rutas a partir del nombre de entorno. El secreto de
enrolamiento se mantiene en un archivo privado; el generador sólo recibe su
ruta y nunca lee ni copia su contenido.

```bash
python3 aux-observe enrollment --server tls.example.org:443   --endpoints /ruta/privada/endpoints.json --ca /ruta/privada/ca.pem   --secret-path /etc/osquery/enroll.secret   --output /ruta/privada/agente-nuevo
```

Sin --apply sólo se presenta el plan. Con --apply se crean flags 0600 dentro de
una carpeta nueva 0700 fuera de las fuentes. El servicio no se reinicia ni se
enrola. Antes de activar, revisar su flagfile, la instalación existente y su
estado; comprobar el certificado y crear el secreto con permisos adecuados.
Activar esos flags autoriza al servidor indicado a proporcionar configuración
y consultas al agente. Verificar después el nodo y sus resultados en osctrl.

Fuentes oficiales consultadas el 17 de noviembre de 2026:
- https://osquery.readthedocs.io/en/stable/installation/install-linux/
- https://osquery.readthedocs.io/en/stable/deployment/remote/
- https://docs.osctrl.net/api/operations/apiv1environments/get/
- https://docs.osctrl.net/api/operations/apiv1nodesenvactive/
- https://docs.osctrl.net/api/operations/apiv1all-queriesenv/
- https://docs.osctrl.net/api/operations/apiv1queriesenvresultsname/
