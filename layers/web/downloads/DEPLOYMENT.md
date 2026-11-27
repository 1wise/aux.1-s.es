# Operación de AUX 8

Timestamp: 2026-11-27 | Version: 8.0.1-beta.8  
Author & Credits: https://www.alawise.es/1-s

## Configuración y migración

Trabajar con una copia revisable de configuración y catálogo. Cada ruta relativa
se interpreta junto al archivo de configuración utilizado. Las claves siguen en
el almacén privado, fuera del código y las raíces públicas.

`./aux catalog migrate --input /ruta/al/perfil.json` muestra la importación.
Admite catálogos/selecciones JSON y listas anteriores como entrada explícita.
`--apply` guarda el resultado en el catálogo configurado. Se combinan recursos por
ID; la lista antigua no se convierte en fuente activa. Para una selección aislada
se puede utilizar `--catalog`.

## Catálogo e IA

```bash
./aux catalog --interactive
./aux catalog preset --preset alpine --preset fedora --apply
./aux catalog set-policy --resource ID --policy E16
./aux catalog set-policy --resource ID --policy E16 --apply
./aux catalog refresh --resource ID --apply
```

Los presets añaden valores sin borrar cambios manuales. Resolver una referencia
dinámica modifica la identidad del artefacto; comprobar de nuevo antes de generar.
Los recursos sin regla única se conservan y se explica el fallo.

Cada guardado genera el sidecar SHA-256 del catálogo. La opción `refresh --commit`
utiliza `catalog_git_repository`, comprueba que el catálogo esté dentro y que Git
tenga identidad configurada, y confirma solo el catálogo y su sidecar. No hace
push ni confirma otros cambios preparados. El temporizador semanal conserva su
calendario; antes de activarlo hay que preparar el repositorio y la configuración
del servicio. Esta entrega no activa el temporizador.

GPT/Gemini permite elegir proveedor, modelo, objetivo y Max tokens. Se revisa la
consulta y se verifican fuentes antes de aceptar. La confirmación final guarda
recursos/políticas en el catálogo; no instala ni acredita pruebas de arranque.

## Inventario de Bastion

En `fast-boot.json`, `checkstatus.bastion` contiene:

| Campo | Uso |
| --- | --- |
| `enabled` | Activar la consulta al servidor configurado. |
| `transport` | `rsync`, `ftps` o `ftp`, según el acceso disponible. |
| `directories` | Pares `path` y `public_url`: directorio remoto y descarga pública. |

FTPS utiliza los campos FTP y el almacén privado. Rsync utiliza los parámetros
SSH de `mirror` y los hosts conocidos de SSH. Hay límites de tiempo, profundidad
y archivos. No hace falta Python en Bastion para listar mediante FTPS o rsync.

Un acceso fallido queda como desconocido/error y conserva la observación positiva
anterior como historia. No se publica como disponibilidad actual. Las rutas
relativas ambiguas requieren separar prefijos o configurar rutas explícitas.

## Descargar, desplegar y generar

La descarga exige SHA-256 fijado, admite parciales con validador HTTP para reanudar
y conserva una copia válida ante un error. Los artefactos distintos se separan.
La descarga y el despliegue requieren sus propios planes y `--apply`.

RAM/disco reutiliza el preparador de ISO. Los componentes se publican por su tipo.
Un stage3 alojado necesita todavía su procedimiento chroot: copiar el archivo no
crea un sistema instalado. La réplica integral sigue en aux-release.

Tras desplegar, ejecutar checkstatus. `generate` consume el inventario y publica
índices, documentación, catálogos y menús; no consulta Bastion durante esa fase.
Los enlaces de Bastion proceden de las URL públicas observadas.

## Prueba hasta login

Arrancar el instalador en el entorno elegido y conservar un log identificable.
Registrar después con `./aux checkstatus --help`. La atestación del operador no
es una interpretación automática del texto del log ni sustituye la prueba real.
Checksum y login son evidencias distintas.

## Instalación, mantenimiento y API

`aux-setup` conserva ISO/base nueva/sistema actual, con el sistema actual al final
y plan confirmado. `aux-enter` conserva inspección, montajes, LVM y chroot;
`aux-observe` conserva osquery/osctrl. Se incluye el contrato anterior
`docs/api/aux-go-openapi-v0.1-draft.yaml` como material de revisión. No se crea un
servidor nuevo de administración ni se modifica el contrato osctrl. Las nuevas
API de mantenimiento/instalación siguen pendientes de definición funcional.
