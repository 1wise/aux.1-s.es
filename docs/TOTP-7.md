# Revalidación TOTP de TEC

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

La autorización del segundo factor dura 14 400 segundos desde el último código
aceptado. El servidor exige otro código al alcanzar cuatro horas. La consulta de
solicitudes, el registro de casos y la emisión de tickets comparten la política.
La actividad no renueva la marca temporal; sólo una nueva verificación correcta
puede hacerlo. El cierre de sesión, la suspensión de una cuenta o una rotación
de semilla pueden invalidar el acceso antes.

El código de seis cifras conserva su periodo de 30 segundos y la protección contra
reutilización. No se restablecen las cuentas, la inscripción TOTP ni las semillas.
La duración TOTP no modifica el plazo de consentimiento del cliente o del caso.

## Vencimiento de las dos terminales

Cada ticket nuevo incluye el vencimiento firmado reauth; exp queda limitado a
ese vencimiento o 60 segundos, lo que ocurra antes. La pasarela valida reauth y
aplica el menor plazo entre su heartbeat de autorización y el tiempo restante.
Ni los mensajes continuos ni la renovación de tickets de la misma verificación
permiten prolongar el transporte. Un código nuevo aceptado sí permite emitir
tickets con un nuevo vencimiento.

Al caducar se cierra el transporte de ambas terminales. Se confirma un código
nuevo en TEC y se reconecta conforme al plazo de consentimiento que siga vigente.
La reconexión no crea un grupo LVM ni modifica los discos. No sustituye las
comprobaciones del arranque, los dispositivos y el montaje actual.

Los tickets anteriores sin reauth siguen aceptándose para permitir la transición
entre versiones. Para aplicar la política completa se actualizan tanto TEC como
la pasarela. La validación HTTP de TEC rechaza el acceso a las cuatro horas;
la pasarela nueva aplica además el límite al transporte WebSocket ya abierto.

## Aplicación en Excalibur

Esta entrega contiene las fuentes completas, no una actualización ya aplicada.
El portal utiliza /var/www/aux.1-s.es/web y la pasarela /opt/aux-cli. Preparar copia
de los componentes anteriores, verificar el manifiesto, comprobar la sintaxis PHP
y Python y sustituir las fuentes públicas según la instalación existente.
Conservar la configuración privada, cuentas, semillas, casos y secretos del nodo.
El reinicio de la pasarela afecta a los transportes activos y debe hacerse al
terminar la sesión de pruebas. Cambiar las aplicaciones en la RAM de la Live no
actualiza estos componentes del servidor. Este ajuste no requiere compilar una ISO.

## Comprobaciones

Las pruebas PHP cubren una validación de más de 15 minutos y de casi cuatro horas,
el rechazo al alcanzar cuatro horas y después, la ausencia de renovación por
actividad, marcas temporales inválidas, otra identidad y rotación de semilla.
La integración HTTP usa PHP real y una pasarela TLS local: comprueba páginas,
solicitudes de ticket, vencimiento firmado y rechazo del registro tras caducar.
La prueba SSH abre dos PTY reales y acorta el reloj de la prueba a segundos para
comprobar que el tráfico y las renovaciones no impiden el cierre del transporte.
No se afirma una prueba de cuatro horas de duración ni un despliegue en producción.

Referencia para la caducidad absoluta y su control en servidor: [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#absolute-timeout).
