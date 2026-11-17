# Verificación

Timestamp: 2026-11-17 | Version: 7.0.1-beta.4
Author & Credits: https://www.alawise.es/1-s

Ejecutar desde la raíz fuente:

```bash
python3 -m compileall -q auxlib
python3 -m unittest discover -s tests7
node tests7/test_origin_portal.cjs
```

Las pruebas de interfaz verifican F1, conservación de valores, confirmaciones
incorrectas y selección atómica. Las pruebas de observación usan procesos
simulados y un servidor HTTPS local con una CA de prueba: autenticación,
redirecciones, errores, paginación y redacción de secretos. Las pruebas de
preparación de enrolamiento contrastan planes sin escritura, modos privados y
rechazo de sobrescrituras. No se contacta con una flota real en estas pruebas.

Las comprobaciones del portal revisan enlaces locales, plantillas y sumas del
paquete completo. La aceptación de hardware, ISO y firmware se realiza en los
equipos de destino. El éxito de una prueba automatizada no se presenta como
prueba física ni como publicación real en Excalibur o Bastion.
