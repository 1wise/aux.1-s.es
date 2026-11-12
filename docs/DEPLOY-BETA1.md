# Continuar el despliegue desde beta.0

Timestamp: 2026-11-10 | Version: 7.0.0-beta.19  
Author & Credits: https://www.alawise.es/1-s

Trabajar en la carpeta nueva después de extraer el paquete completo. Comparar
fast-boot.json con el del servidor antes de aplicar cambios. No copiar state,
credenciales ni datos privados al repositorio o al árbol público.

1. Comprobar la entrega: `sha256sum -c --quiet SHA256SUMS`.
2. Abrir `python3 aux-catalog -i`. F5 / Rastrear consulta metadatos usando la
   configuración incluida; la cuarta pantalla elige url.txt o una lista personalizada.
3. Revisar Sincronizar listas locales. Sólo las reglas explícitas se aplican;
   APLICAR guarda copias *.before-crawl. Las 49 URL actuales están cubiertas; un error conserva el catálogo y las listas.
4. `bash download.sh -i`: revisar lista, caché y concurrencia. Los archivos
   existentes válidos se reutilizan salvo que se pida volver a descargarlos.
5. `bash deploy.sh -i`: elegir disco/RAM/FTP y revisar el plan. El perfil de
   URLs no conecta a otro servidor. Los límites y comprobaciones físicas del
   despliegue se conservan; no borrar RAM ni caché para resolver espacio a ciegas.
6. `bash generate.sh -i`: usar el catálogo actualizado state/catalog/current/catalog.json
   o indicar otro mediante --catalog-file. Generar escribe los índices/menús y
   conserva copias de los archivos generados que sustituye en cache/backups.

Excalibur tiene una caché existente de 62 GiB y un directorio RAM observado de
26 GiB. La disponibilidad tmpfs indicada inicialmente fue 18 GiB. Son medidas
de la sesión, no garantías de espacio futuro. Consultar el plan antes de añadir
imágenes. El catálogo de enlaces remotos no necesita almacenar esas imágenes.

Bastion requiere comprobar sus rutas, capacidad y método de acceso antes de
transferir. FTP replica el árbol publicado y la caché completos, no una sola lista.
La contraseña se pide localmente y nunca se guarda en la configuración pública.
