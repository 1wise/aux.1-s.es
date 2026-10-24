# AUX Assist 6.2 — agente con aprobación local

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

Fuentes de pruebas, NO una ISO compilada ni una versión estable. Se conserva la
ISO Rescue 5.0.1 y no se ha modificado ningún servicio en Excalibur/Kamala/OVH.

## Ubicación de cada servicio

| Lugar | Servicios | Función |
| --- | --- | --- |
| Excalibur | `aux-cli`, Nginx, PHP-FPM TEC | SSH web de técnico y portal |
| ISO | `aux-gpt`, `aux-gemini` | Clientes API sin root, usuario `aux-ai` |
| ISO | `aux-exec` | Recibir propuestas por socket Unix, sin operación remota de aprobación |
| ISO, F6 opción E | `aux_exec.py review` | Revisar y aplicar/deshacer como root, solo en `/dev/tty6` |

La API OpenAI/Gemini se consulta DIRECTAMENTE por HTTPS. El servicio `cli.1-s.es`
de esta entrega transporta asistencia humana SSH; NO es una pasarela API de IA.
Las respuestas de API son sesiones nuevas y no contienen este chat ni sus memorias.
Un «hola mundo» allí no aparecerá en esta conversación sin copiarlo aquí.

Las claves se introducen en F4/F5 con V visible (por defecto) u O oculta.
La entrada visible queda en la terminal; hacia la API solo viajan por HTTPS.
No hay fichero de claves ni transcripción persistente. Python no garantiza borrado
criptográfico de memoria; RAM, volcados y swap deben protegerse en el despliegue.
No pegar claves en este chat, en el terminal de conversación ni en comandos.

## Acciones de la primera entrega

| Acción | Alcance | Deshacer |
| --- | --- | --- |
| `diagnostic` | memoria, lista de discos sin datos de usuario, servicios fallidos | No hay cambios que deshacer |
| `write_file` | `*.txt` sencillo bajo `/work/managed`, máximo 8192 bytes, modo 0600 | Copia previa exacta o retirar SOLO el archivo creado |
| `service_state` | iniciar/detener exclusivamente `chronyd.service` | Restituir active/inactive; no revierte efectos externos del servicio |

No se ejecutan shell libre, scripts, sudo generado por IA, instalación/retirada de
paquetes, cambios de red, configuraciones del sistema, firmware ni operaciones de
disco. DNF history no garantiza un deshacer general: paquetes anteriores pueden
no estar disponibles y los scriptlets pueden tener efectos no reversibles. Esa
ampliación permanece PENDIENTE, no se sustituye por una promesa de rollback.

Las propuestas caducan a los 10 minutos. Cada autorización se vincula al ID y al
SHA-256 exacto del plan. No se permite reutilizar una acción aplicada. Deshacer
requiere nueva confirmación, hasta una hora desde la propuesta, y comprueba que
el destino no cambió. Dos consolas/proveedores comparten un bloqueo local. Una
acción interrumpida queda `needs_review`, no «deshecha». Reiniciar el broker cancela
propuestas pendientes. No existe continuación automática de cambios tras un fallo.

El diario privado y las copias anteriores viven en `/run/aux-exec/state`
(root 0700, archivos 0600); se pierden al reiniciar. El registro de auditoría omite
contenido de archivos, prompts y respuestas. `/work` sigue siendo tmpfs. **No se
promete deshacer después del reinicio.** `/storage` no conserva ese diario por defecto.

## Ensayo «hola mundo»

1. Compilar la receta nueva; las unidades no aparecen en una ISO antigua por cambiar la web.
2. Arrancar la ISO, G para GPT o M para Gemini. Indicar modelo habilitado y clave API sin eco.
3. Escribir `hola mundo`. Comprobar la respuesta de cada proveedor por separado.
4. Pedir: `Propón crear hola.txt con el texto Hola mundo en el área gestionada.`
5. `/planes` debe mostrar `pending`. Todavía NO existe el archivo.
6. Ctrl-Alt-F6 → E → `listar` → `simular ID` → `aplicar ID`.
7. Revisar motivo, texto, destino, estado anterior y SHA-256. Escribir la frase
   `APLICAR ID primeros12delSHA` mostrada por la consola.
8. Volver a F4/F5 → `/resultado ID`. Se presenta el resultado localmente. Solo
   escribir `ENVIAR` si se desea comunicarlo a la API. No hay envío automático.
9. `/deshacer ID` solo solicita deshacer. F6 → E → `deshacer ID`, revisar y confirmar
   con la nueva frase. Verificar desde T que el archivo se retiró/restauró.
10. En E, `revocar` impide nuevas acciones. En el menú, I detiene ambos clientes API.

La autorización física separa al modelo del ejecutor, pero no limita a un
administrador root o técnico SSH ya autorizado: root puede modificar cualquier
programa. No conceder SSH root y asumir simultáneamente aislamiento frente a ese técnico.

## Pruebas locales

```bash
python3 test_exec.py
python3 test_ai.py
python3 test_sources.py
```

Son pruebas de código con fixtures de proveedor y escritura real en directorios
temporales. No llaman a APIs facturables ni cambian servicios, paquetes o discos
del host. El entorno de preparación bloquea AF_UNIX: la prueba de socket real se
marca omitida y DEBE ejecutarse en la ISO. Faltan API reales, arranque BIOS/UEFI, SELinux Enforcing, revisión
independiente y sesión desde GSM. Mantener `stable_ready: false` hasta documentarlas.

Referencias de protocolo: https://developers.openai.com/api/docs/guides/function-calling
y https://ai.google.dev/gemini-api/docs/function-calling . Se conservan en RAM los
elementos originales de respuesta, incluidos identificadores de llamada y firmas
de pensamiento Gemini; el esquema estricto no sustituye la validación local.
