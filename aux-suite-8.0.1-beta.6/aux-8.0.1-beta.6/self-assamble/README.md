# Self-assamblers

Timestamp: 2026-11-22 | Version: 8.0.0-beta.7
Author & Credits: https://www.alawise.es/1-s

Carpeta de trabajo para los asistentes GPT y Gemini que proponen transformaciones de la suite.

- `requests/`: solicitudes con objetivo, módulos y revisión de origen.
- `proposals/`: respuestas JSON y diffs pendientes de revisión.
- `builds/`: copias nuevas generadas tras revisar una propuesta.

```sh
./aux self-assamble --describe
./aux self-assamble --goal 'Preparar un laboratorio' --output self-assamble/requests/laboratorio.json
./aux self-assamble --interactive
./aux self-assamble --proposal self-assamble/proposals/propuesta.json
./aux self-assamble --proposal self-assamble/proposals/propuesta.json --apply --output self-assamble/builds/laboratorio
```

Las claves API se conservan en la configuración privada o el entorno, nunca en esta carpeta. La consulta real muestra sus límites antes de confirmarla. Las fuentes originales se conservan; las pruebas de la copia creada quedan pendientes hasta ejecutarlas. Las solicitudes, propuestas y construcciones locales se excluyen de Git, de los paquetes y de las copias generadas.
