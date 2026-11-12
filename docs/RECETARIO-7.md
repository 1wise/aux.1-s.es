# Recetario netboot y seguimiento por revisión

Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

La beta.6 prepara el intercambio de recetas mediante recipes.json, recipes.html
y recipes.manifest.json en los perfiles exportados. Sólo publica recetas
aprobadas localmente. Las candidatas quedan en el perfil de trabajo.

Cada revisión tiene un identificador SHA-256 calculado sobre la receta y la
identidad del medio. Cambiar argumentos, arquitectura o medio produce otra
revisión. El hash identifica contenido; no prueba que arranque correctamente.
El registro distingue la revisión HTTP de las pruebas reales de hardware.
profile_assistance describe el perfil que exportó la revisión; no atribuye
individualmente todas las recetas a la última consulta de un proveedor.

## Propuesta para la siguiente capa

Una ficha de receta actúa como hilo: versiones, comentarios, incidencias,
propuestas de API y resultados de arranque. Las revisiones exportadas se adjuntan
por su identificador, conservando el historial. El seguimiento no necesita un
foro general ni otra base de cuentas.

TEC dispone actualmente de cuenta confirmada y perfil de técnico aprobado.
Un recetario dinámico debe reutilizar esa autenticación, con estos permisos:

| Participación | Operaciones propuestas |
|---|---|
| Visitante | Consultar recetas publicadas y su historial público. |
| Cuenta confirmada | Proponer, comentar y seguir recetas. |
| Cuenta con cuota API | Solicitar preparaciones dentro del presupuesto autorizado. |
| Revisor | Evaluar propuestas y registrar evidencias de BIOS/UEFI por equipo. |
| Moderación | Gestionar publicación, incidencias y permisos. |

La cuota de API y los permisos técnicos son dimensiones independientes.
Pagar una preparación no convierte la propuesta en una receta validada.

Cada solicitud de pago necesita identidad de cuenta, proveedor/modelo, reserva
de presupuesto, resultado y consumo informado por el proveedor. Una clave de
idempotencia evita relanzamientos automáticos del mismo trabajo; si el resultado
de una llamada es incierto, se revisa antes de repetirla. Las claves permanecen
en el servicio de ejecución, separadas de comentarios y recetas públicas.

Las pruebas requieren datos específicos: revisión, arquitectura, firmware,
equipo y resultado. Una comprobación HTTP o un comentario favorable no sustituye
esas evidencias. Los datos de contacto y los diagnósticos privados de TEC se
mantienen fuera del registro público de recetas.

El foro, los comentarios, la cola multiusuario, la contabilidad y los cobros
no están implementados en beta.6. No se ha creado una pasarela de pago ni se
han hecho llamadas facturables durante las pruebas de esta entrega.
