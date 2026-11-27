# Corrección de catalog.sources.json en configuraciones personales

Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
Author & Credits: https://www.alawise.es/1-s

Una configuración antigua en ~/.config/aux/config.json podía resolver la ruta predeterminada config/catalog.sources.json dentro de ~/.config/aux/config/, aunque las reglas están incluidas en el directorio config/ de la suite. Ocurría también cuando esa ruta errónea había quedado guardada como absoluta.

La beta.4 utiliza el archivo incluido cuando falta esa referencia predeterminada. Una copia existente junto a la configuración tiene prioridad. Las rutas personalizadas se conservan: si falta su archivo, el mensaje identifica catalog_sources_file y la forma de configurarlo. No se crean reglas vacías ni se sustituye el catálogo seleccionado. Las rutas de caché, salida, catálogo y estado siguen resolviéndose respecto a la configuración.

Para corregir una instalación anterior desde la raíz de fuentes:

```sh
./aux-config set catalog_sources_file "$(realpath config/catalog.sources.json)"
```

El campo también está disponible en INPUT / OUTPUT y catálogos del configurador interactivo, con ayuda F1. No requiere rehacer la imagen iPXE ni volver a descargar distribuciones.

Ocho pruebas cubren clave ausente, ruta relativa antigua, ruta absoluta antigua, copia local existente, rutas personalizadas, error explicativo, separación de rutas mutables y ejecución CLI real desde la configuración personal.
