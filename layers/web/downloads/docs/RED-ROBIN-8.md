# Blue Hibou y Red Robin — despliegue y precauciones

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9  
Author & Credits: https://www.alawise.es/1-s

Blue Hibou identifica las notas y procedimientos de despliegue rápido. Red Robin identifica avisos y precauciones; la etiqueta RED TEAM señala herramientas u operaciones que requieren especial atención. La etiqueta describe su capacidad e impacto operativo, no acusa al programa de ser malicioso ni acredita una auditoría de seguridad.

| Área | Riesgo concreto | Medida operativa |
| --- | --- | --- |
| aux-assist, SSH, Cockpit y gateways | Abrir terminales o administración con privilegios y exponer servicios a la red. | Selección opcional; comprobar identidad, destino, puertos, firewall/VPN y consentimiento; revisar el cierre. |
| Instalación en sistema actual | Cambiar paquetes, cuentas, servicios o configuración del equipo real. | Revisar hostname y plan antes de APLICAR; contar con recuperación y acceso local. |
| RAM y tmpfs | Agotar memoria que usan el sistema y otros procesos, aunque la cuota nominal parezca suficiente. | Leer MemAvailable; conservar reserva; reducir selección y concurrencia. |
| Caché, extracción y réplicas | Consumir SSD, inodos, ancho de banda e I/O; un árbol extraído puede crecer más que su ISO. | Separar imágenes/deploys, comprobar espacio real y dejar margen. |
| Escrituras y arranque USB | Escribir en un destino equivocado o modificar datos y cargadores. | Identificar ruta y dispositivo; verificar sumas y copias antes de grabar. |
| Tareas permanentes y cargas intensivas | Mantener CPU, RAM, I/O o red ocupados durante tiempo indefinido. | Definir duración, límites, supervisión y parada antes de habilitar un servicio o timer. |

## Herramientas remotas

AUX Assist y el rol de administración que contiene Cockpit quedan fuera de la selección inicial. Se pueden elegir expresamente. La base conserva el cliente SSH y deja de incluir el servidor SSH; la tarea Debian ssh-server también queda sin preseleccionar. Instalar un paquete no equivale a autorizar una intervención. Las unidades propias de asistencia siguen siendo de inicio manual; los paquetes de la distribución pueden iniciar servicios o sockets según sus políticas. Revisar el estado y los puertos reales después de instalar.

La acción local de Cockpit muestra la advertencia y exige escribir INICIAR COCKPIT antes de iniciar cockpit.socket. La web prepara la selección y abre una URL indicada; no instala ni inicia servicios en los servidores por sí misma. El cliente de asistencia mantiene sus controles de consentimiento, identidad y cierre. Antes de permitir root, verificar el contacto y la huella del técnico.

## Cuotas, disponibilidad y carga

Los presets 10 GiB RAM / 75 GiB SSD por preset son propuestas para una máquina de referencia. No son un requisito para usar AUX ni una reserva física. El tablero mantiene las previsiones y los límites configurados; una máquina compartida necesita valores menores y margen para su trabajo habitual.

Antes de una nueva descarga de tamaño conocido se contrasta el espacio pendiente con el sistema de archivos de caché, dejando 1 GiB de reserva. Antes de desplegar se comprueba el destino local: en RAM se usa MemAvailable y se conserva al menos 512 MiB o el 20 % de MemTotal, el mayor; en disco, 1 GiB. Las comprobaciones no sustituyen la medición del árbol extraído ni un límite de CPU, I/O o memoria por proceso. No pueden reservar capacidad frente a otros procesos concurrentes.

No se habilitan nuevas cargas de estrés ni tareas permanentes mediante el tablero. Cualquier futura herramienta de carga debe incluir alcance, duración, límites efectivos y una parada verificable. Un timer, socket o daemon necesita revisión propia, además de la cuota del catálogo.

## Cierre de la intervención

Cerrar la sesión autorizada y comprobar que los accesos temporales han terminado. Revisar servicios y sockets que se hayan iniciado, procesos, montajes, cuentas o claves temporales y tareas programadas. Conservar el informe y las evidencias necesarias. No detener servicios ajenos a la intervención sin conocer su función.

Los avisos aparecen junto a las herramientas, en los planes y en la documentación; los emblemas no sustituyen el texto, para que las precauciones sigan siendo legibles en Links, consola y lectores de pantalla.
