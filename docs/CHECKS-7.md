# Comprobaciones de 7.0.0-beta.15

Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
Author & Credits: https://www.alawise.es/1-s

| Comprobación | Resultado |
|---|---|
| python3 -m unittest discover -s tests7 -q | 201 pruebas aprobadas. |
| TOTP cuatro horas | PHP real: aceptación después de 15 minutos y antes de cuatro horas; rechazo a las cuatro horas; identidad, rotación y actividad sin prórroga. HTTP real frente a TLS local: páginas/tickets/registro y vencimiento firmado comprobados. |
| Selector con objetos | Seis regresiones para diccionarios, valores iguales, listas, None, booleanos/números, búsqueda y opciones inválidas. |
| AUX Enter en PTY real | Selección del dispositivo, modo y LV, seguida de cancelación en ABRIR sin traceback. La operación de almacenamiento se sustituye durante esta prueba. |
| AUX Enter / LVM | Quince regresiones: informes multi-PV, selección por UUID, límites de dispositivos, activación/limpieza, LV existente, modo RO, cancelación y raíz activa. Informes y dispositivos simulados. Ensayo real aportado en una VM de 4 GiB con LV lineal ext4: montaje RO, LV existente conservado y activación temporal con cierre comprobados. |
| tmux Live | Payload compartido incluye ratón, 20 000 líneas, tmux-256color y barra derecha. Arrastre real pendiente; el entorno impide crear el socket Unix de tmux. |
| Tamaño y teclado web | Node ejecuta el Fit original contra dimensiones controladas: fuentes, resize, panel oculto y Shift+PgUp/PgDn aislados. PHP real/TLS y carga del nuevo HTML comprobados. La geometría visual real sigue pendiente. |
| ncurses | Comprobaciones de utilidades ausentes, terminfo ausente y ejecución real de infocmp/tput en el entorno de pruebas; la receta verifica también las entradas antes de finalizar. |
| Ensayo externo beta.11 | Compilación y mediacheck PASS comunicados; arranque llega a Bash con aviso de tmux.conf. No se presenta como validación de LVM. |
| Metadatos netinst | Seis regresiones: .discinfo sin .treeinfo, formato alternativo, versión/arquitectura, conflictos, ausencia y diagnóstico xorriso. Transporte xorriso simulado. |
| Fuentes Live | 71 pruebas: 64 aprobadas y siete omitidas por requerir root. |
| Links sin documentación | RPM oficial links-2.30-7.fc45 inspeccionado: binario links2 y alternativa links condicionada al manual. Registro real en directorios temporales probado sin manuales. |
| Pasarela CLI | 19 pruebas aprobadas: dos PTY sobre SSH real, caducidad bajo tráfico continuo, límite firmado aunque se renueven tickets, cierre y cliente antiguo. |
| Menú de asistencia | Dos pruebas de integración aprobadas: medio antiguo manual y capacidad declarada para selección automática. |
| Constructor Fedora 45 | Plan, identidad del instalador, checksum, KVM, RAM, destino y empaquetado público comprobados con entradas locales y entorno VM simulado. Lorax no ejecutado aquí. |
| Imagen destacada | PNG de la entrega idéntico byte a byte al adjunto; 1254 x 1254. |
| Metadatos y pie | Open Graph/Twitter y descarga del PNG original; portada con pie lateral y alternativa móvil. Rutas anidadas comprobadas. |
| Marcas superiores | AUX/PXE/TEC conservados; favicon y aux-logo.png originales conservados. |
| Portada y texto | Referencias de origen, familias adicionales y enlaces iPXE presentes en HTML estático, PHP y vistas de texto. |
| JavaScript | Modelo, filtros, enlaces de origen, diálogo y ausencia de copias locales inventadas comprobados con DOM simulado en Node. |
| Taller de recetas | Inventario público acotado, medios separados, modos conservados, HEAD sin cuerpos, dependencias y aprobación individual. |
| Registro de revisiones | Sólo recetas aprobadas; identificadores cambian con la receta; cada revisión publicada tiene su lanzador. |
| Terminal beta.6 | AUX RECETAS abierto en PTY 120 x 30; Escape sale sin traceback ni llamada API. |
| Memtest normal / GRUB | ZIP reales en directorios temporales: separación, despliegue en ambos órdenes, repetición y descubrimiento por generate. Sólo la identificación de tmpfs está simulada. |
| Destinos ambiguos | Se rechazan tanto listas como descubrimiento de caché antes de publicar. |
| Propiedad de árboles | Un enlace ajeno sigue protegido; la corrección no autoriza sustituir otros árboles. |
| Fedora secundaria | Arquitecturas s390x y ppc64le y versión 45 conservadas. |
| Actualización beta.5 (histórico) | Dos módulos completos con copias numeradas; configuración, selección y estado conservados. Beta.6 requiere actualizar también el generador y sus recursos. |
| GPT / Gemini | Peticiones y respuestas estructuradas simuladas; rechazo de respuestas incompletas, campos desconocidos y credenciales en perfiles. |
| Fuentes nuevas | Resolución local de versiones y tamaños; patrones acotados, separación stable/testing/beta y origen cuando no cabe o no se resuelve. |
| Perfiles de réplica | Exportación independiente, límites persistentes, Default local opcional, Custom y conservación de defaults AUX. |
| Recetas iPXE | Datos tipados, revisión local, cabeceras HTTP y guardas de arquitectura/firmware; no se certifica arranque. |
| Kali SHA256SUMS | Pruebas de delegación HTTPS acotada del manifiesto; los demás índices/API conservan sus restricciones. |
| Terminal real (beta.4) | Diálogos API y perfil abiertos y cancelados en PTY de 120 x 30; regreso al catálogo y salida sin traceback ni llamada API. Véase terminal-beta4-results.json. |
| Generación | Ensayo con perfil exportado e integración del submenú; el dry-run no crea directorios de publicación ni caché. |

Las 166 pruebas del conjunto principal de beta.8 se conservan. Las trece nuevas
cubren el constructor Live, el paquete integrado, la selección de asistencia
y la inspección de los metadatos del instalador.
La receta generada se compila como Python para comprobar la sintaxis de %post.
La ISO beta.13 no se ha construido ni probado en BIOS/UEFI en este entorno.
La descripción REST pública de Gemini confirmó responseMimeType,
responseJsonSchema y maxOutputTokens. No se hicieron consultas de pago ni se
validó un modelo concreto de una cuenta.

El ensayo real del checksum de Kali desde este entorno terminó con
Temporary failure in name resolution. El nuevo rastreo de las 49 descargas
debe comprobarse en Excalibur; no se afirma un resultado HTTP completo.
Los ensayos locales no montan ISO reales ni prueban estas recetas en BIOS/UEFI.
El estado HTTP no sustituye checksums, firmas o pruebas de arranque.

El renderizado Chromium no pudo ejecutarse porque el entorno rechazó la creación
de su socket. No se presenta la prueba DOM como una comprobación visual de navegador.
Las respuestas de proveedores API y sus recursos de prueba siguen simulados.
El foro multiusuario, la contabilidad y los pagos no están implementados.
