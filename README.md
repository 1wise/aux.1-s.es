# AUX 8.0.1-beta.9 / Matrioshka

Cuatro entregas hermanas en la raíz: suite completa ZIP, aux-pxe ZIP, tec-cli ZIP e imagen básica de arranque USB .img. Cada archivo tiene SHA-256. La web preparada es una capa auxiliar; no es una quinta imagen de producto.

Plan sin escritura:

    python3 DEPLOY.py --web-root ./web-para-subir

Crear la web con las cuatro descargas:

    python3 DEPLOY.py --web-root ./web-para-subir --apply

Preparar también un directorio de trabajo como el repositorio: fuentes en suite/ y las cuatro entregas a su lado:

    python3 DEPLOY.py --web-root ./web-para-subir --sources-root ./repositorio-aux --apply

Usar destinos nuevos. El Git original conserva sus metadatos; no se empaquetan .git, credenciales ni historial privado. Un clon del repositorio tiene las cuatro entregas en el mismo nivel que .git y suite/. Los paquetes son salidas del árbol suite/, por lo que no se incluyen recursivamente a sí mismos.

Para Bastion sin Python, preparar localmente y subir el contenido de web-para-subir por FTPS. La imagen .img ya está sin comprimir y se usa con la herramienta habitual para grabar USB. Este desplegador no escribe discos ni instala servicios.

La imagen básica es el bootstrap iPXE existente para BIOS y UEFI x86_64, sin nueva aceptación hasta login ni Rescue Linux recién compilada. Las fuentes de Rescue siguen disponibles.

24 MB es el límite de fuentes de la suite; módulos duplicados, las cuatro entregas y el envoltorio se contabilizan aparte. Los self-assamblers trabajan en suite/self-assamble/ dentro del directorio de trabajo extraído.
