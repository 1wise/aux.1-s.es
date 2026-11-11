# Referencia 6.4 y migración pendiente

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

La suite 6.4 recuperada se conserva íntegra en `reference-6.4/`. Es una referencia
de código y de interfaces; sus instrucciones Live no son las de construcción
de esta edición estándar. Mantiene sus versiones, atribuciones y licencias.

## Extraer solamente para estudiar las fuentes

```bash
mkdir -p work/reference64
unzip reference-6.4/aux-suite-6.4.0-dev.1.zip -d work/reference64
mkdir -p work/reference64/assist-source
unzip work/reference64/aux-assist-6.4.0-dev.1-sources.zip \
  -d work/reference64/assist-source
```

No ejecutar automáticamente su instalador web, constructor portable o `%post`
antiguo. Las cuentas, casos y claves de los servidores se respaldan y migran
por separado; una edición documental nueva no los modifica.

## Mapa de trabajo sobre AUX Assist

| Fuente 6.4 | Trabajo requerido para sistema estándar |
|---|---|
| `payload/assist.py` | Texto de edición/distribución, directorios persistentes, lanzamiento XFCE y config tmux común. |
| `payload/agent.py` | Revisar servicio web de asistencia, dos PTY, configuración tmux y ciclo de revocación. |
| `payload/support_case.py` | Separar autorizaciones persistentes de `aux.persist=1` y de la detección de Live USB. |
| `payload/work.py` y `tech-work.service` | Sustituir workspace RAM por rutas persistentes estándar; no activar sin adaptar. |
| `payload/storage.py` | Quitar supuestos de etiqueta/partición de la llave anterior y conservar selección explícita de destino. |
| `portable/runtime.py` y `portable/portable_menu.py` | Arquitectura antigua de overlay; no constituyen el constructor de disco instalado nuevo. |
| `aux-assist.service` y `aux-observer@.service` | Revisar condición de kernel, privilegios, TTY y coexistencia con XFCE. |
| `remote-shell.sh` | Conservar selección fija de las dos terminales y rechazo de comandos arbitrarios. |
| `ai.py`, `ai_agent.py` y unidades API | Adaptar claves, directorios persistentes, dependencias y límites configurables. |
| `aux_exec.py` | Mantener revisión del plan y contexto inequívoco del sistema de destino. |

La configuración tmux antigua generaba `mouse off`. El archivo
`config/tmux.conf` incorpora los ajustes acordados y debe convertirse en fuente
común de los generadores de sesiones. El archivo efímero de `/run` no es su
fuente canónica.

Fedora y Debian difieren en nombres de unidades, rutas y políticas de seguridad.
No deshabilitar SELinux/AppArmor para hacer pasar una prueba. La adaptación
requiere comprobar permisos y el contexto de ejecución real de cada servicio.

## Componentes de servidor

La suite incluye AUX/PXE, TEC y aux-cli. Conservar la actualización coordinada
de web, gateway y cliente cuando cambie el protocolo. La primera entrega 7 de
cliente debe declarar sus capacidades reales y conservar o migrar explícitamente
las rutas y contratos 6.4 que se reutilicen.

El extractor de rutas y el generador PXE existentes sirven de punto de partida
para el crawler; las nuevas recetas necesitan procedencia, arquitectura,
versiones y comprobación del servidor desplegado. No marcar el crawler como
implementado por haber añadido únicamente un ejemplo JSON.

## Alcance honesto de esta entrega

Están preparados la guía manual, las selecciones iniciales, las plantillas de
instalación y configuración y esta lista de adaptación. La recuperación de
fuentes no convierte todas las mejoras propuestas en software terminado.
Se puede empezar a instalar y comprobar la base estándar mientras se porta
AUX Assist. No publicar la imagen como una suite 7 completa de asistencia hasta
superar la aceptación de la guía 08.

