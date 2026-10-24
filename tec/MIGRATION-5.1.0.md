<!-- Timestamp: 2026-10-13 | Version: 5.1.0 | Author & Credits: https://www.alawise.es/1-s -->

# Cuenta única y perfiles públicos

Antes de actualizar el servidor, poner TEC en mantenimiento y respaldar el directorio privado /var/lib/aux-assist. Guardar la copia con 0700 y sus JSON con 0600, fuera de html, web y FTP. Conservar técnicos, solicitudes, límites y sesiones; no publicar el respaldo.

Instalar el paquete 5.1.0 y el JSON central fuera de la raíz web. Ejecutar como el usuario del pool TEC:

    php manage.php init
    php manage.php migrate-users
    php manage.php users
    php manage.php list
    php manage.php requests

La migración crea usuarios.json, vincula los técnicos por usuario_id y conserva IDs de técnicos, hashes de contraseña y solicitudes. Es idempotente. Una colisión con un registro no confirmado ajeno a la migración requiere revisión administrativa. Los JSON usan el mismo lock y reemplazo atómico por archivo; no constituyen una transacción de varios archivos. Mantener el respaldo hasta validar cuentas, correo y solicitudes. Las cuentas antiguas de técnicos confirmados siguen admitidas mientras se completa la migración.

El registro web es único: confirmar el correo activa el usuario. El usuario puede pedir asistencia o una instalación a un técnico aprobado, enviar correo al administrador y solicitar su propio rol de técnico. No hace falta confirmar cada nueva solicitud cuando la cuenta ya está confirmada. Los registros antiguos de solicitudes mantienen su confirmación original.

La aplicación profesional incluye URL, empresa/proyecto, biografía y clave pública. El correo y teléfono proceden de la cuenta. Solicitar o modificar un perfil lo deja pendiente de revisión. La ficha y profiles.php publican email, teléfono, URL, empresa, biografía y clave pública solamente para perfiles aprobados; nunca password_hash ni tokens. Completar empresa y biografía de perfiles antiguos con el formulario antes de una nueva aprobación.

Administración:

    php manage.php approve tec_ID
    php manage.php suspend tec_ID
    php manage.php suspend-user usr_ID
    php manage.php activate-user usr_ID
    php manage.php password usr_ID
    php manage.php resend usr_ID

Aprobar exige correo confirmado. Suspender un técnico retira su perfil profesional; suspender un usuario bloquea su cuenta y oculta los perfiles vinculados. El contacto al administrador usa tec.admin_mail, con Reply-To de la cuenta confirmada. CSRF, cookies y límites por dirección siguen activos; los formularios no necesitan JavaScript. mail() significa aceptación por el MTA, no entrega garantizada.

No se ha migrado el servidor real ni se han enviado correos reales durante esta publicación.
