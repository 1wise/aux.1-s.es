# CDN: primer piloto para AUX

Timestamp: 2026-11-27 | Version: 8.0.1-beta.7  
Author & Credits: https://www.alawise.es/1-s

Inventario y réplica Excalibur/Bastion deben funcionar antes del piloto. La CDN
añade distribución HTTP con caché; no acredita réplica ni pruebas de arranque.

1. Revisar el apartado CDN del alojamiento OVH: oferta incluida/contratada o
   disponible y dominios afectados.
2. Elegir un dominio piloto y unos pocos archivos públicos estáticos versionados,
   por ejemplo estilos e imágenes.
3. Preparar reglas de duración de caché, actualización y purga para esa oferta.
4. Verificar origen/CDN, contenido/hashes y actualización tras publicar una nueva
   versión, conservando una vía de acceso al origen.
5. Evaluar aparte ISO grandes y componentes: tamaño admitido, reanudación,
   solicitudes parciales y cliente iPXE concreto.

El catálogo mutable, menu.ipxe, sesiones, formularios TEC/CLI y API requieren
tratamiento propio; el primer piloto no los incorpora automáticamente a caché.
Este paquete no modifica DNS, contrata opciones ni activa CDN.

Referencia oficial consultada el 22/11/2026:
https://docs.ovhcloud.com/en/guides/web-cloud/web-hosting/cdn-how-to-use-cdn

Los límites deben comprobarse para el servicio concreto; un cupo de precarga no
se toma como límite general de tamaño de una ISO.
