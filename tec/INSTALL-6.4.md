# Instalar AUX 6.4.0-dev.1

Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
Author and Credits: https://www.alawise.es/1-s

## Preparación en Excalibur

Descomprimir la suite en un directorio nuevo. Los cinco ZIP permanecen juntos
con `install-web.py`, `fast-boot.json.example` y `SHA256SUMS`.

```bash
sha256sum -c SHA256SUMS
python3 install-web.py --help
```

El instalador mantiene el modo de plan por defecto. Usar la configuración vigente
del despliegue para conservar dominios, rutas, certificados y almacenamiento privado.
La guía INSTALL-6.3.md incluida mantiene la preparación de usuarios, PHP-FPM,
Nginx, secretos y copias; aplicar esas instrucciones con los paquetes 6.4.

Actualizar conjuntamente AUX/PXE, TEC y aux-cli. Los datos privados y el registro
de casos se conservan. El plan debe mostrar la configuración y las rutas del
servidor antes de aplicar. Comprobar Nginx y la salud del gateway tras la instalación.

## Compilar la ISO en Bebe

Las fuentes `aux-assist-6.4.0-dev.1-sources.zip` incluyen su README, `prepare.py`,
`finish.py` y todas las pruebas. Usar Fedora 44 x86_64, KVM y el netinst oficial
verificado. La receta sigue ejecutándose solo dentro de la VM de construcción.

```bash
python3 test_sources.py
python3 test_network.py
python3 test_ai.py
python3 test_exec.py
python3 prepare.py --output work-6.4.0-dev.1 --config fast-boot.json.example
ksvalidator -v F44 work-6.4.0-dev.1/assist.ks
```

Continuar con el comando de Lorax y `finish.py` del README de las fuentes. El
constructor USB `aux-portable-6.4.0-dev.1-kit.zip` debe recibir esa nueva ISO
para que ambos perfiles incluyan las dos terminales y la corrección de DNS.
El plan del constructor es de lectura; no sustituir ni formatear una llave usada
como parte de esta preparación. Conservar los datos de la llave antes de migrarla.

## Aceptación funcional

Desde CLI, confirmar segundo factor, aceptar la solicitud y esperar AUTORIZO en
el cliente. Open two terminals abre otra pestaña con Terminal 1 y Terminal 2.
Comprobar comandos distintos, pegado de varias líneas y Ctrl+C en cada terminal.
Al salir de una shell, la otra debe continuar. Cerrar asistencia desde el panel
debe cortar las dos. Verificar también la reconexión autorizada del USB persistente.

Arrancar el perfil persistente y el limpio en BIOS y UEFI. Comprobar DHCP y
`getent ahostsv4 cli.1-s.es`, repetir tras reiniciar y comprobar N/nmtui sin cable.
Estas pruebas de arranque siguen pendientes de realizar con la nueva ISO compilada.
