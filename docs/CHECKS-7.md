# Comprobaciones de 7.0.0-dev.4

Timestamp: 2026-11-10 | Version: 7.0.0-dev.4  
Author & Credits: https://www.alawise.es/1-s

| Comprobación | Resultado |
|---|---|
| python3 -m unittest discover -s tests7 -q | 58 pruebas aprobadas. |
| Prueba DOM del instalador con jsdom 26.1.0 | ISO predeterminada, sistema actual al final y explícito, aux-assist opcional, catálogos y exportaciones coincidentes con Python. |
| Terminales TEC | Aprobado: retención, aislamiento, UTF-8, pegado, reconexión y autorización. |
| Catálogo HTML estático | 186 entradas netboot disponibles como enlaces sin JavaScript; origen predeterminado. |
| Fedora 45 | Índice de imágenes y comps oficiales consultados; 155 grupos y 20 entornos. Repositorios y perfil del instalador apuntan a 45. |
| Rastreo real de las tres fuentes configuradas | Publicación de metadatos y enlaces, sin imágenes descargadas. |
| Política local | Selección obligatoria, límite de cantidad/bytes, menús excluidos de caché, reutilización y conservación de copias previas. |
| aux-assist | Instalación en raíz temporal con y sin selección; conserva configuración existente; elección propagada a ambos perfiles ISO. |
| Destino | --apply sin --mode/--selection se rechaza antes de ejecutar un gestor de paquetes. |

Reproducir la prueba DOM con jsdom 26.1.0 disponible en Node:
node tests7/test_installer_ui.cjs. AUX_JSDOM permite indicar una instalación
externa de esa dependencia de pruebas; no es una dependencia de producción.

Pendiente: instalación real Fedora/Debian, ISO nueva, BIOS/UEFI, Secure Boot,
LUKS/chroot en VM, revisión visual en navegador, resolución completa de paquetes,
activación del temporizador en Excalibur y publicación remota. El informe de
dev.2 se conserva como histórico; las pruebas PHP/API no se declaran repetidas.
No se han enviado cambios a GitHub ni publicado el Site anterior.
