# Terminales, historial y ncurses

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

## Ajuste de la ventana

El área de terminal recibe el espacio que queda después de la cabecera, estado,
herramientas, pestañas y controles. Las herramientas se pueden desplegar. La vista
baja se compacta para conservar espacio para la terminal. La regla del panel tiene
prioridad sobre el estilo compartido de section del portal.

El complemento oficial Fit 0.11.0 utiliza las celdas del renderizador xterm 6.0.0.
El xterm incluido se conserva byte a byte; las versiones y SHA-256 de los recursos
están en tec/web/vendor/terminal-assets.json. Los recursos se sirven desde TEC,
sin CDN ni dependencia de Node en producción. CSS y JavaScript cambian de URL de
versión para evitar conservar la vista anterior en caché.

El tamaño se vuelve a calcular al cambiar de pestaña, ventana o fuente. Se agrupan
los cambios en un frame y se conserva el límite de 20–300 columnas y 5–150 filas
del gateway. Cada cambio llega únicamente al PTY de su terminal.

## Historial

Dentro de tmux, el historial pertenece a tmux. La configuración mantiene 20 000
líneas, activa el ratón y habilita pane-scrollbars a la derecha, con ancho de dos
celdas y colores cyan/indigo. La barra requiere un tmux que admita esa opción;
las opciones silenciosas permiten conservar el teclado en versiones anteriores.
Fedora 45 distribuye una versión con soporte de barras.

La rueda y el arrastre sobre esa barra navegan por el historial remoto. Las teclas
Shift+PgUp/PgDn se envían a tmux en lugar de intentar mover el búfer local vacío
de su pantalla alternativa. En el historial, q vuelve al shell. Las aplicaciones
que capturan el ratón siguen recibiendo sus eventos habituales.

La sesión web usa la configuración común sin barra de estado adicional. La sesión
SSH directa conserva el aviso de consentimiento en su barra de estado y reutiliza
la misma configuración de historial y terminal.

## ncurses en la Live

La receta solicita ncurses, ncurses-base y ncurses-term. Además de las bibliotecas,
la imagen debe contener clear, tput, reset e infocmp. El postinstalador comprueba
las definiciones linux, xterm-256color, screen-256color y tmux-256color. Si falta
una utilidad o entrada, la construcción termina con un diagnóstico explícito.

Para preparar la Live de pruebas ya arrancada, desde root y las fuentes completas:

```bash
dnf install -y ncurses ncurses-base ncurses-term
install -m 0644 config/tmux.conf /usr/share/aux-assist/tmux.conf
tmux -S /run/aux-assist/tmux.sock source-file /usr/share/aux-assist/tmux.conf
```

Estos cambios residen en la RAM de la Live; la próxima ISO debe construirse con
la receta nueva para conservarlos al arrancar de nuevo.

## Publicación y aceptación

La vista se actualiza en TEC con el directorio tec/web completo, incluido vendor.
Conservar antes una copia del componente público y comprobar la sintaxis PHP.
Las cuentas, semillas, configuración privada y casos permanecen fuera de esa raíz.
La actualización web y la de la Live son componentes distintos; actualizar sólo
la copia de las aplicaciones en /usr/local/lib/aux no publica el portal TEC.

Comprobar en las dos pestañas:

1. Generar varias pantallas de salida con seq 1 300.
2. Subir y bajar con la rueda y arrastrar la barra derecha; q sale del historial.
3. Probar Shift+PgUp/PgDn y verificar que la otra terminal no se desplaza.
4. Cambiar de pestaña, abrir/cerrar herramientas, cambiar el tamaño de ventana
   y repetir con una ventana estrecha y con zoom; el prompt debe quedar dentro.
5. Ejecutar clear y comprobar que la aplicación sigue recibiendo el teclado.

El ensayo Node ejecuta el complemento Fit original con celdas y fuentes controladas,
y prueba los atajos, la separación de pestañas y la liberación de observadores.
La integración usa PHP real y una pasarela TLS local. Las comprobaciones de ncurses
usan también infocmp y tput reales. El navegador de pruebas no pudo acceder a la
vista local y el entorno impide crear el socket Unix de tmux: no se presenta esto
como una comprobación visual del arrastre ni como una ISO beta.15 ya arrancada.

## Referencias

- [Manual de tmux](https://man.openbsd.org/tmux#pane-scrollbars).
- [Fit y complementos de xterm](https://xtermjs.org/docs/guides/using-addons/).
- [ncurses de Fedora](https://packages.fedoraproject.org/pkgs/ncurses/ncurses/).
