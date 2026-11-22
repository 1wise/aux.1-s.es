# Cierre beta.3: catálogo, matrioshka y self-assamblers

Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
Author & Credits: https://www.alawise.es/1-s

Se añaden los 69 perfiles de Ei al catálogo AUX, que pasa a 283 registros. La máscara propuesta se descarta. Se conservan nombres, versiones propuestas, arquitecturas, URLs, artefactos y procedencia. Se muestran como referencias de origen; la importación no activa descargas ni acredita arranques. Para Finnix, cuyo registro no aportaba URL, se enlaza su página de descarga del proyecto. La auditoría anterior sigue distinguiendo 140 URL comprobadas, 74 para revisión y 69 incorporadas sin nueva auditoría.

Los asistentes de transformación se llaman **self-assamblers**. `./aux self-assamble` es la entrada principal y `evolve` continúa como alias. La carpeta `self-assamble/` trae `requests/`, `proposals/` y `builds/`. Puede crearse una copia nueva en builds; la carpeta de trabajo se excluye de la copia, del contexto enviado y de futuras entregas, evitando recursión o publicación de trabajo privado.

El presupuesto es **24.000.000 bytes de fuentes de la suite**. El archivo completo de despliegue puede ocupar más: contiene una matrioshka con capas web, fuentes e imagen mínima, verificadas por separado. No se cuenta repetidamente el código presente en varias capas para medir el presupuesto de la suite. MANIFEST.json distingue el árbol de fuentes, los archivos comprimidos y el tamaño bruto de la imagen.

```sh
python3 package-matrioshka.py --source-zip /ruta/aux-suite-8.0.0-beta.3.zip --output /ruta/aux-matrioshka-8.0.0-beta.3.zip
```

Extraer el envoltorio y ejecutar su DEPLOY.py. El modo predeterminado muestra un plan; --apply exige un directorio web nuevo. La web incluye las descargas de la suite y la imagen. --sources-root permite extraer además las fuentes a un destino de trabajo separado. Para Bastion se prepara el árbol localmente y se sube su contenido por FTPS; el alojamiento no necesita Python. No se cambian servicios del sistema ni se graba ningún disco.

La imagen mínima incluida es la imagen iPXE actual de 13.887.488 bytes, con SHA-256 verificado, para BIOS y UEFI x86_64. No es una Rescue Linux nueva ni una prueba de login. El código de Rescue se conserva en la suite para construirla y probarla después.
