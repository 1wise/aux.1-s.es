# GPT Assist / Gemini Assist · 6.3.0-dev.1

Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
Author & Credits: https://www.alawise.es/1-s

La ISO incluye G (GPT, F4) y M (Gemini, F5), con retorno al menú por F6.
I detiene ambos servicios API. Cambiar de terminal no cierra una sesión.

Los servicios se ejecutan como el usuario fijo aux-ai, sin root ni capacidades.
Por defecto usan --agent: proponen acciones a aux-exec y requieren aprobación
física en F6/E. El protocolo y sus límites están en AGENT-6.3.md.
Este documento describe también el modo consulta al iniciar ai.py sin --agent,
que solo intercambia los mensajes escritos y no ofrece herramientas.

## Configuración pública

La raíz `fast-boot.json` tiene una sección `ai` exportada por prepare.py al
`ai.json` público de la ISO. Con el ZIP de receta independiente se puede editar
`ai.json` y preparar sin --config. `model: null` solicita un modelo al iniciar;
si se fija, debe ser un identificador habilitado en la cuenta de ese proveedor.
No se inventan modelos ni se selecciona uno automáticamente.

```json
{
  "enabled": true,
  "openai": {"model": null},
  "gemini": {"model": null},
  "timeout_seconds": 60,
  "max_output_tokens": 1024
}
```

`enabled: false` oculta las opciones locales e iPXE y rechaza iniciar el cliente.
Los modelos y límites son públicos. La clave se pide en modo V visible u O oculto cada vez que se
inicia el proceso; no se añade al JSON, la ISO, GRUB, iPXE, argumentos, URLs ni
historial de shell. No hay variables con claves en el servicio. La conversación
se conserva solo en memoria del proceso; /nueva borra ese contexto local.
Reiniciar o detener el servicio libera su memoria; Python no garantiza borrado
criptográfico de cadenas. El tratamiento en el proveedor depende de su API y
cuenta: el borrado local no elimina datos que ya se hayan enviado.

Cada consulta tiene un límite de salida y un timeout. El historial tiene un
máximo local de 16 turnos y 64 KiB antes de una nueva consulta; /nueva reinicia
el contexto. Los errores HTTP, DNS o TLS se muestran sin copiar cuerpos de
error. No hay reintentos automáticos para evitar repetir consultas en red GSM.
Una sesión necesita una clave API propia y conectividad HTTPS al proveedor.

## GRUB e iPXE

El comando de compilación de README.md incorpora `aux.ai.available=1`.
finish.py reconoce esa declaración y duplica la entrada Live en dos entradas
manuales: GPT Assist y Gemini Assist. Añaden respectivamente `aux.ai=openai` o
`aux.ai=gemini`. El arranque normal sigue siendo la primera opción a 5 segundos.
Si se desactiva `ai.enabled`, esas entradas GRUB vuelven al menú sin abrir la API.

Después de desplegar la nueva ISO y ejecutar generate, iPXE ofrece `0.A` si
encuentra una imagen de asistencia completa que declara ese marcador. Usa los
mismos kernel, initrd y SquashFS de esa imagen: no se duplica su almacenamiento.
La asistencia normal sigue siendo el autoarranque de 60 segundos. Una ISO antigua
sin declaración de soporte no recibe entradas AI.

## Verificación

```bash
python3 test_ai.py
python3 test_sources.py
python3 prepare.py --output work-6.3.0-dev.1 --config ../fast-boot.json
```

El ZIP independiente de receta omite la comprobación de integración iPXE porque
no incluye generate.sh; esa comprobación se ejecuta con el proyecto completo.
En ese ZIP, preparar sin --config usa ai.json y cli.json de la misma carpeta.

En la ISO nueva: G o M, introducir modelo y clave en la terminal correspondiente,
enviar una pregunta pequeña, revisar respuesta y /salir. Volver con Ctrl-Alt-F6
y comprobar `systemctl is-active aux-gpt.service aux-gemini.service` desde T.
Repetir con red ausente, clave inválida y límite de cuota. Revisar con SELinux
Enforcing, USB tethering GSM y las dos opciones de GRUB/iPXE. Estas pruebas
reales de API y arranque quedan pendientes: las pruebas de fuentes usan fixtures
y no consumen cuentas ni cuotas.

## Referencias de API

- OpenAI Responses: https://developers.openai.com/api/docs/guides/text
  POST https://api.openai.com/v1/responses, autorización Bearer y `store: false`.
- Gemini generateContent: https://ai.google.dev/api/generate-content
  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent,
  clave en cabecera `x-goog-api-key`.

Los certificados TLS se verifican con las CA del Live. No se siguen redirecciones
con las claves. No existe una opción para desactivar esa verificación.

El perfil USB persistente 6.3 admite claves preparadas por separado en
AUX/private/api/openai.key y gemini.key. G/M permiten L para cargarlas, además de
V/O manual. K guarda, sustituye o borra; I cierra los asistentes y conserva los
archivos de la llave. No se inician consultas solo por guardar una clave.
