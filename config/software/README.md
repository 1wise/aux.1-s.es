# Catálogos nativos de software

Timestamp: 2026-11-10 | Version: 7.0.0-beta.19  
Author & Credits: https://www.alawise.es/1-s

Los JSON incluidos proceden de metadatos oficiales descargados el 2026-11-09.
Son instantáneas reproducibles, no una consulta en tiempo real del destino.
El manifiesto de selección exige la misma suma de catálogo al importar.

| Distribución | Fuente y transformación |
|---|---|
| Debian Testing / amd64 | tasksel-data 3.91, debian-tasks.desc; 230 tareas. Nombres y metapaquetes contrastados con Packages.xz de testing/main/amd64. standard expande los 104 paquetes de prioridad required/important/standard del índice. |
| Fedora 45 / x86_64 | repomd.xml y su comps XML; 20 entornos y 155 grupos. La suma comps comprimido coincide con repomd. Los entornos conservan grupos requeridos, opcionales y predeterminados. |

Cada JSON registra URL de procedencia, sumas de entrada, rama y arquitectura.
La coincidencia con estos índices no declara verificadas sus firmas. El gestor
nativo del destino utiliza su configuración de repositorios para resolver e
instalar paquetes. No se sustituyen ni desactivan sus comprobaciones de firmas.

Fedora instala los paquetes mandatory/default y conditional que correspondan
según DNF; elegir un grupo no solicita todos sus paquetes opcionales.
Debian instala los metapaquetes de cada tarea; sus dependencias siguen en APT.
Los 230 IDs incluyen las tareas de idiomas. La interfaz permite encontrarlas
mediante búsqueda o mostrando idiomas; Fedora permite mostrar grupos internos.

auxlib/software.py contiene los lectores de tasksel y comps, las validaciones
y la resolución de elecciones. Permite importar un XML comps local con
`python3 -m auxlib.software --help`. El lector Debian requiere además un JSON de
metadatos con packages y standard, derivados del índice de la misma rama.
Tras renovar las instantáneas, revisar los cambios y reconstruir la web; una
selección anterior se rechaza hasta volver a exportarla bajo el catálogo nuevo.

La atribución y licencia de tasksel se conservan en DEBIAN-COPYRIGHT.
Los nombres y descripciones de Fedora proceden de sus metadatos comps.
