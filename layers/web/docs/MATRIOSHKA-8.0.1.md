# AUX 8.0.1-beta.6 — cuatro entregas junto al Git

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9  
Author & Credits: https://www.alawise.es/1-s

La versión pasa a 8.0.1-beta.6 al cerrar el uso de los 24 bits. PASCDE conserva sus posiciones y contratos: los cuatro bits P son usuario, tendencia del sector, obligatorio y sugerido por IA para el sector. No hay una migración adicional de bits ni se cambian las decisiones del catálogo.

La matrioshka reúne cuatro entregas hermanas en la raíz del repositorio, al mismo nivel que .git y suite/:

| Archivo | Contenido |
| --- | --- |
| aux-suite-8.0.1-beta.6.zip | Suite completa de fuentes con ambos módulos. |
| aux-pxe-8.0.1-beta.6.zip | Catálogo, Netboot, web y herramientas AUX/PXE. |
| tec-cli-8.0.1-beta.6.zip | Comunidad, cuentas y asistencia TEC/CLI. |
| aux-minimal-ipxe-8.0.1-beta.6.img | Imagen básica USB iPXE, ya sin comprimir. |

Cada entrega tiene su .sha256. RELEASE.json identifica las cuatro, sus tamaños y hashes. La imagen USB conserva el bootstrap existente BIOS/UEFI x86_64; no acredita una nueva Rescue Linux ni una prueba hasta login.

Las fuentes viven en suite/. Los cuatro paquetes se generan fuera de ese árbol para evitar que el paquete completo se incluya recursivamente a sí mismo. El límite de 24.000.000 bytes corresponde al árbol fuente de la suite; las entregas repetidas y el envoltorio se contabilizan aparte.

Desde suite/, preparar las cuatro entregas en la raíz del Git:

    python3 package-release.py --output ..

Conservar una entrega publicada inmutable; usar un destino nuevo para una reconstrucción de revisión. Crear el envoltorio exterior:

    python3 package-matrioshka.py --source-zip ../aux-suite-8.0.1-beta.6.zip --output ../release-artifacts/aux-matrioshka-8.0.1-beta.6.zip

El ZIP exterior contiene las cuatro entregas en su raíz, sus hashes, el desplegador y la web como capa auxiliar. Los metadatos .git no se incluyen en el ZIP. El repositorio Git real conserva su historial y contiene las cuatro entregas.

Después de extraer la matrioshka, revisar el plan:

    python3 DEPLOY.py --web-root ./web-para-subir --sources-root ./repositorio-aux

Aplicar después de revisar:

    python3 DEPLOY.py --web-root ./web-para-subir --sources-root ./repositorio-aux --apply

La web recibe las cuatro descargas. El directorio de trabajo recibe suite/ y, a su lado, las mismas cuatro entregas. Se eligen destinos nuevos; todos los hashes, ZIP y rutas se validan antes de crearlos. El desplegador acepta también las matrioshkas antiguas de tres capas sin cambiar su extracción anterior.

La imagen .img puede usarse con la herramienta habitual de grabación USB. DEPLOY.py solo prepara archivos y no escribe dispositivos. Para Bastion sin Python, preparar la web localmente y subir su contenido por FTPS.

Se conserva Kernel Modeler. Las aportaciones de AP continúan en revisión independiente y no sustituyen el catálogo ni sus resoluciones comprobadas.

El límite de 24 MB corresponde a la suite completa. Réplicas, secciones e imagen básica se contabilizan aparte. La capa web reutiliza los recursos idénticos de las cuatro entregas y los restaura automáticamente al desplegar; los paquetes de producto permanecen completos. Se validan esas referencias antes de escribir. El límite del alojamiento por archivo es independiente del presupuesto del proyecto.
