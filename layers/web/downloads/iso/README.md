# ISO y perfiles AUX

Timestamp: 2026-11-23 | Version: 8.0.1-beta.6
Author & Credits: https://www.alawise.es/1-s

Abrir `python3 aux-images --interactive`. Las opciones preparan un instalador
ISO oficial personalizado, perfiles Kickstart/preseed, una receta Live, una
construcción Live en VM KVM o un archivo de imagen USB. Revisar el plan de cada
generador; no confundir la receta con una ISO ya compilada.

El medio de entrada debe ser un archivo existente. El campo SHA-256 requiere
64 cifras hexadecimales y se contrasta con los bytes. La fuente de confianza
es el proveedor; una suma local no sustituye la comprobación de su firma.
Elegir una salida nueva, fuera de /dev y con directorio padre disponible.

Los perfiles Debian/Fedora conservan tareas y grupos nativos y añaden los
componentes AUX seleccionados. El constructor debe comprobar los paquetes en
repositorios compatibles con su rama. No se garantiza que una receta o un
perfil de otra arquitectura pueda ejecutarse sobre el constructor actual.

El generador USB crea un archivo. No graba un dispositivo físico. La capacidad
se expresa en bytes positivos múltiplos de 512. GENERAR confirma el plan;
Esc cancela. Los errores de capacidad, rutas y sumas se corrigen sin abandonar
el campo.

La aceptación requiere construir en el entorno adecuado, verificar hashes y
probar los medios con la arquitectura y firmware de destino. Secure Boot
requiere una cadena firmada y de confianza; el cliente iPXE incluido no
acredita por sí mismo esa compatibilidad.
