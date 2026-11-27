# TEC · adaptador opcional para Sites

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
Author & Credits: https://www.alawise.es/1-s

El módulo distribuido `tec-cli` incluye el foro nativo PHP en `tec/web/forum.php`,
con cuentas TEC y JSON privado. Este directorio conserva exclusivamente el
adaptador opcional para Sites; sus datos e identidades son independientes.

El adaptador funciona en `/forum` con almacenamiento D1 y formularios HTML de servidor.
La opción `?view=pxe` usa la presentación terminal. Lectura, búsqueda, aportaciones,
respuestas y moderación no requieren JavaScript. El acceso conserva la audiencia
configurada en Sites; preparar el foro no lo convierte en un servicio público.

Se admiten recetas, errores, peticiones y soluciones. La evidencia declarada se
clasifica como probada, simulada, descubrimiento o hipótesis. Temas y respuestas
entran pendientes; la autoría y moderación pueden leerlos antes de su publicación.
Cada revisión conserva responsable, fecha y motivo. Una receta revisada en el foro
no se convierte automáticamente en un lanzador iPXE aprobado.

La identidad procede de Sites. El identificador estable del visitante vincula las
aportaciones; el nombre público se elige en el formulario y el correo no se publica.
`FORUM_MODERATOR_EMAILS` configura el alta inicial de moderadores. Al aportar por
primera vez, el rol queda vinculado al identificador estable en `forum_members`.
Conservar este valor en la configuración del servicio, fuera del repositorio.

El export JSON contiene solo temas publicados y señala que la importación al
catálogo exige revisión. Las migraciones están en `drizzle/`, fuera de las rutas
públicas. No incluir la base de datos en las réplicas de ISO ni en paquetes fuente.

La aplicación de asistencia PHP existente continúa siendo independiente. Este
foro usa el servicio Worker de Sites: copiar `forum.mjs` a PHP-FPM no lo ejecuta.
El dominio `tec.1-s.es` requiere desplegar o enrutar este servicio en esa
infraestructura; esta publicación no cambia DNS ni el servidor TEC externo.

Comprobación desde la raíz del proyecto hospedado:

```sh
node --test suite/tec/forum/forum.test.mjs
python3 build_site.py
python3 check_site.py
```
