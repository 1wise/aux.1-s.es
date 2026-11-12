# AUX · Aplicación de entrada unificada

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

La entrada `aux` reúne las aplicaciones existentes en una consola menuconfig.
Es la base de integración prevista para la alfa: presenta los recorridos y llama
a cada herramienta, manteniendo sus comandos independientes y sus comprobaciones.
La integración de consola no declara completada la aceptación de toda la plataforma.

Desde las fuentes descomprimidas:

```bash
./aux
```

Tras instalar las herramientas o construir una Live con esta entrega:

```bash
aux --interactive
```

| Menú principal | Aplicación existente |
|---|---|
| Preparar imágenes y medios | aux-images: instalador ISO, perfil, receta Live, construcción Live en KVM y USB persistente. |
| Catálogo, selección y recetas iPXE | aux-catalog: selección, rastreo, límites y taller GPT/Gemini. |
| Servidor | download.sh, deploy.sh y generate.sh, cada uno con --interactive. |
| Sistemas y chroot | aux-enter --interactive. |
| Asistencia local | aux-assist: apertura explícita de los controles físicos en VT6. |
| Herramientas del equipo | Cockpit y área de trabajo web local de aux-tools. |
| Perfiles de software | aux-profile --interactive. |
| Instalar y personalizar | aux-setup: preparación de ISO primero e instalación sobre el sistema actual al final. |

El menú principal usa índigo y cada aplicación conserva su nombre y tema propio.
Los generadores y tareas de despliegue usan cyan. La selección se maneja con
flechas y Enter; Q/Esc vuelve desde un submenú y sale desde la raíz. Se conserva
la posición elegida al regresar. Al terminar o cancelar una aplicación, Enter
regresa al menú AUX. Un fallo del hijo se muestra antes de continuar.

Los planes, destinos, confirmaciones y requisitos de permisos pertenecen a las
aplicaciones llamadas. El lanzador conserva el intérprete Python actual y las
rutas del mismo árbol de fuentes; los scripts Bash siguen ejecutándose con Bash.
La ausencia de un componente se comunica y permite regresar al menú.

`aux-tools --interactive` abre la misma entrada unificada. Sus opciones --gui y
--tool siguen abriendo su destino directamente. `aux --help` y `aux --version`
funcionan sin terminal interactiva. El instalador añade el lanzador `aux` y su
acceso de escritorio; la receta Live lo incluye en las fuentes verificadas.

Ocho regresiones cubren rutas, intérpretes, retorno, posiciones, cancelación,
errores, contexto de color, modo sin TTY y compatibilidad de aux-tools. Una prueba
con PTY real abre AUX IMAGES, lo cancela y vuelve al menú principal sin construir
ningún medio ni iniciar una instalación. Los demás hijos se verifican mediante
su registro y pruebas propias; no se ejecutan despliegues reales en esta prueba.
