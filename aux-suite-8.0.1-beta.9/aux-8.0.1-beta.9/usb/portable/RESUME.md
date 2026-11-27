# Reanudación de asistencia · 6.3

Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
Author & Credits: https://www.alawise.es/1-s

Implementada en las fuentes; pendiente de aceptación en una ISO arrancada.

El perfil personalizable arranca primero tras 5 segundos. Una autorización inicial
incluye continuar tras reinicios en el mismo equipo durante ocho horas. Antes de
AUTORIZO aparecen técnico, huellas, alcance y hora UTC de vencimiento. Una nueva
conexión no amplía ese plazo.

El registro privado AUX/private/support/case.json está ligado al UUID USB, UUID
DMI del equipo, técnico, claves aprobadas y vencimiento. Contiene la credencial de
reanudación y la clave de host SSH del caso, con permisos root 0600. Las claves API
son opcionales e independientes; véase API-KEYS.md. Un equipo diferente, permiso
caducado, reloj atrasado o archivo no privado impiden reanudar automáticamente.

En web, CLI conserva el caso en /var/lib/aux-cli/cases; no guarda el token del
cliente en claro. Mantiene la clave SSH del gateway y la asignación al técnico.
El agente verifica el mismo caso, técnico, claves y plazo antes de restaurar SSH.
Cerrar desde TEC o F6 elimina el permiso. Un reinicio del gateway conserva los
casos vigentes; una revocación con el cliente apagado se respeta al volver.

Si el perfil TEC aportó clave pública, la autorización web puede incluir la ruta
SSH directa 4242. Ambas huellas aparecen antes de autorizar. Sin esa clave solo
se abre loopback. Esa ruta C también espera la validación de CLI al reanudar.
C iniciada localmente con URL de clave usa un caso local; su cierre es desde F6
o con `python3 /usr/share/aux-assist/support_case.py close`, dentro del cliente.
No tiene un registro TEC ni promete revocación remota desde ese portal.

Durante el reinicio TEC muestra reconectando. La terminal ya abierta vuelve a
conectarse cuando el agente esté listo, siempre con un ticket vigente del técnico.
La sesión o el TOTP del técnico pueden requerir renovación. La consola vuelve
con una shell nueva: los procesos y tmux anteriores terminaron en el reinicio.

SIGTERM al apagar preserva el caso. Ctrl-C en F6 cierra el caso; en C local también
lo cierra Enter. El perfil limpio no lee ni modifica la autorización persistente.
Los errores de transporte cierran SSH mientras se reintenta; no abren un acceso
nuevo a un técnico diferente. La identidad DMI no sustituye una atestación TPM.

Pruebas de fuentes: cinco casos cliente (identidad, reloj, privacidad, clave de
host y cierre/apagado), cinco de gateway (incluido reinicio del servicio y dos
terminales SSH reales sucesivas), más flujo DOM de reconexión TEC. Faltan reinicio
real del cliente, BIOS/UEFI del Live, SELinux enforcing, Wi-Fi/DHCP y USB físico.
