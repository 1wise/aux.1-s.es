# AUX / PXE / TEC 6.1.0-dev.1

Timestamp: 2026-10-17 | Version: 6.1.0-dev.1
Author & Credits: https://www.alawise.es/1-s

Fuentes de pruebas. **No estable ni ISO 6.1 compilada.** No se han modificado
Excalibur, Kamala, OVH, DNS o cuentas. No se han utilizado claves API.

## Cambios

- G/M proponen acciones mediante function calling, sin root. El modo consulta
  anterior continúa disponible iniciando ai.py sin --agent.
- Ejecutor común con socket Unix y revisión física F6/E: mostrar plan, SHA-256
  y estado previo; simular, confirmar, aplicar y deshacer.
- Diagnósticos acotados, *.txt en /work/managed y arranque/parada de chronyd.
  Propuestas de 10 minutos, bloqueo compartido, prevención de reaplicación,
  comprobación de cambios ajenos y registro privado sin contenido sensible.
- Paquetes, red, discos, shell libre y cambios generales de /etc bloqueados.
  No existe deshacer universal. El diario y /work se pierden al reiniciar.
- Bastion B/P/T, ISO y árboles bajo UNA raíz. Materialización física; datos
  privados, cuentas, sesiones, correo y claves fuera de la raíz pública.
- USB con plan por defecto, confirmación reforzada, SHA-256 y AUX-DATA en el
  espacio restante. Solo GPT compatible; prueba física PENDIENTE.
- Montaje opt-in en /storage; /work sigue en RAM. La actualización persistente
  de sistema/kernel sigue PENDIENTE: almacenar una ISO no actualiza el arranque.
- cli/preflight.sh comprueba servicios Excalibur sin modificarlos.

## Entrega

aux-suite-6.1.0-dev.1.zip contiene aux-pxe, tec-platform, aux-cli y
aux-assist-sources como ZIP independientes, con sus SHA-256. La guía vigente es
RELEASE-6.1.md y el estado vigente CHECKLIST-6.1.json. Los documentos de 6.0 se
conservan como contexto histórico, no como prueba de 6.1.

El ZIP aux-pxe incluye USB/OVH. El ZIP aux-assist-sources incluye receta, payload,
pruebas y fast-boot.json.example público. La ISO Rescue 5.0.1 permanece intacta.

## Bebe: receta nueva

Extraer la entrega en un directorio nuevo, verificar sus cuatro archivos .sha256
y extraer aux-assist-6.1.0-dev.1-sources.zip en iso-assist-6.1. Dentro:

```bash
python3 test_executor.py
python3 test_ai.py
python3 test_sources.py
python3 prepare.py --output work-6.1.0-dev.1 --config fast-boot.json.example
ksvalidator -v F44 work-6.1.0-dev.1/assist.ks
```

Usar resultados NUEVOS y el procedimiento livemedia-creator en VM de README.md,
con este Kickstart y la ruta REAL de la ISO Fedora netinst. No usar --no-virt,
no borrar compilaciones anteriores ni recompilar sobre el USB arrancado.
Ejecutar finish.py después de compilar para conservar el arranque híbrido.
El creador USB puede rechazar ese formato si no es GPT protector admitido:
no forzarlo; mantener el método de grabación ya probado mientras se valida.

Actualizar fuentes no añade servicios a una ISO ya construida. Tras arrancar
la imagen nueva (no en Bebe/Excalibur), comprobar:

```bash
systemctl cat aux-gpt.service aux-gemini.service aux-executor.service
```

## Excalibur

Instalar/configurar aux-cli con cli/README.md, conservando secretos actuales si
TEC ya está conectado. Backend 127.0.0.1:8096, HTTPS público y TLS verificado;
no exponer puertos internos. Desde el ZIP CLI: `bash preflight.sh`; desde el
proyecto completo: `bash cli/preflight.sh`. Revisar antes de recargar Nginx.

**aux-gpt, aux-gemini y aux-executor van en la ISO, no en Excalibur.**
CLI transporta SSH humano, no API de IA. Cada agente usa HTTPS directo con clave
propia introducida en memoria. No hay proxy IA central en esta entrega ni claves
incluidas en el USB. No asumir que la facturación API está cubierta por el chat:
verificar las cuentas, modelos habilitados y cuotas de cada proveedor.

## Hola mundo y aceptación

Seguir iso-assist/AGENT-6.1.md: hola mundo en ambas API → proponer hola.txt →
comprobar pending → simular → aprobar F6/E → verificar → solicitar deshacer →
aprobar otra vez → comprobar restauración. Solo ENVIAR comparte el resultado con
la API. Una sesión API nueva no hereda este chat ni envía mensajes a este hilo.

Pendientes: API reales, ISO BIOS/UEFI/SELinux, GSM externo, navegador, caducidad y
revocación físicas, B/P/T sin Excalibur, Kamala, USB real y revisión de seguridad.
Gentoo/Memtest siguen pendientes del error exacto y modo BIOS/UEFI.

## Pruebas reproducibles

```bash
python3 iso-assist/test_executor.py
python3 iso-assist/test_ai.py
python3 iso-assist/test_sources.py
python3 verify-v61.py
python3 verify-v6.py
python3 verify.py
python3 cli/test_cli.py
```

Las pruebas CLI requieren el entorno virtual y dependencias de cli/requirements.txt.
Los informes distinguen lo ejecutado localmente de las pruebas físicas pendientes.
No se cambia la licencia existente. Los componentes de terceros conservan sus licencias.
