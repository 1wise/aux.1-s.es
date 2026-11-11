# Norma visual de aplicaciones AUX

Timestamp: 2026-11-10 | Version: 7.0.0-beta.15  
Author & Credits: https://www.alawise.es/1-s

| Función | Fondo | Ejemplos |
|---|---|---|
| Configurar o seleccionar | Índigo | Catalog, Tools, Enter |
| Instalar, generar o construir | Cyan | Setup, Profile, Images, Live Recipe, USB Image |

El color acompaña a un nombre de aplicación y a una función escrita. No reemplaza
el aviso de destino, la revisión del plan ni la confirmación. Los terminales sin
color conservan inversión y negrita; con ocho colores el índigo usa azul.

La implementación compartida está en auxlib/console_ui.py. El contexto aplicacion
identifica nombre/tipo y se restaura al salir o cancelar. paleta determina los
colores; selecciona y campo implementan listas, casillas, grupos y entrada de datos.
Los diálogos se invocan mediante --interactive. Los argumentos CLI se conservan.

La consola del catálogo conserva la navegación y contabilidad específicas de su
dominio y reutiliza la misma paleta. Los generadores conservan sus validadores,
comprobaciones de hash y dependencias de construcción; la interfaz no los sustituye.
Las confirmaciones de reparación y las shells existentes conservan sus protocolos.
Los componentes históricos independientes no se han rediseñado por completo.

Download, Deploy y Generate usan -i / --interactive con el mismo tema cyan.
El plan se calcula con el --dry-run del propio comando, se muestra completo
y requiere EJECUTAR para aplicar. El catálogo ofrece F5 para rastrear y una
acción separada para revisar/aplicar reglas de sincronización de listas.
