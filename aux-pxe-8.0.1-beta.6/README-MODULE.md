# aux-pxe · 8.0.1-beta.6

Extraer en un directorio vacío.

Plan sin modificar el sistema:

    python3 install-web.py --modules aux-pxe

Aplicar después de revisar rutas, dependencias y TLS:

    sudo python3 install-web.py --modules aux-pxe --apply

Los vhosts son opcionales con --nginx. No se instala el otro módulo.
Guía: docs/MODULES.md. Los paquetes no incluyen ISO, cuentas ni secretos.
