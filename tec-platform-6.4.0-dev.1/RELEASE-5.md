# TEC 5.0.2

Timestamp: 2026-10-12 | Version: 5.0.2
Author & Credits: https://www.alawise.es/1-s

TEC se despliega independientemente en tec.1-s.es / tec.1-s.eu. El paquete
incluye web/, manage.php y nginx.conf.example. AUX/PXE solo enlaza al servicio.
Se conservan los JSON privados y variables AUX_ASSIST_* para facilitar migración.
El correo usa la raíz TEC y las cookies se limitan al nuevo host. Consultar
README.md antes del cambio para DNS, TLS, correo, SELinux y redirects antiguos.
