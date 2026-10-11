<div align="center">

# 🚀 PXE Deployment & Management Suite
*Un ecosistema modular y automatizado para el despliegue de redes, arranque remoto y gestión de portales.*

![Status](https://img.shields.io/badge/status-en%20depuraci%C3%B3n-orange?style=flat-square)
![Version](https://img.shields.io/badge/versensi%C3%B3n-4.2.0-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Linux%20%2F%20USB%20%2F%25Web-lightgrey?style=flat-square)

</div>

---

## 🌟 Descripción General

Este proyecto nace de la iniciativa familiar y técnica por optimizar, automatizar y centralizar los procesos de arranque en red (PXE), despliegue de imágenes y gestión mediante un portal web interactivo. La arquitectura combina scripts de automatización en Bash y Python con una interfaz web moderna y herramientas de verificación robustas para garantizar despliegues limpios y seguros.

Actualmente, el proyecto se encuentra en una **fase activa de depuración**, consolidando la estabilidad de sus componentes antes de su versión de producción definitiva en la rama principal.

---

## 📂 Arquitectura del Proyecto

El repositorio está estructurado de manera modular para separar la lógica de automatización, la interfaz de usuario y los binarios/configuraciones de arranque USB:

```text
.
├── src/                    # 🌐 Código fuente del Portal Web y lógica central
│   ├── index.html          # Interfaz principal de usuario
│   ├── portal.css          # Estilos y diseño visual
│   ├── portal.js           # Lógica interactiva del cliente
│   ├── common.py           # Utilidades y funciones comunes en Python
│   └── DEPLOYMENT.md       # Guía específica de despliegue web
├── usb/                    # 🔌 Configuración y entorno de arranque USB / iPXE
│   ├── bootstrap.ipxe      # Script principal de arranque iPXE
│   ├── general.h           # Cabeceras de configuración general
│   ├── console.h           # Configuración de consola y visualización
│   ├── build.sh            # Script de compilación de la imagen USB
│   └── README.md           # Documentación específica del subsistema USB
├── build.py                # ⚙️ Script general de construcción y empaquetado
├── deploy.sh               # 🚀 Script automatizado de despliegue principal
├── download.sh             # 📥 Gestor de descargas de dependencias y recursos
├── generate.sh             # 🛠️ Generador de artefactos y configuraciones
├── verify.py               # 🔍 Utilidad de verificación del sistema (Python)
├── verify-portal.cjs       # 🔍 Script de pruebas y validación del portal (Node.js)
├── TESTING.md              # 🧪 Protocolo y pautas de pruebas
└── fast-boot.json          # ⚡ Configuración de inicio rápido
```

---

## ⚙️ Mecánica de Despliegue y Uso

> **Nota:** La operativa estándar del despliegue y uso diario se encuentra documentada en los manuales específicos (`DEPLOYMENT.md` y `TESTING.md`) incluidos en el repositorio.

### 1. Preparación y Descarga de Dependencias
Antes de ejecutar cualquier rutina de compilación o despliegue en entornos limpios, asegúrate de recuperar los recursos necesarios:
```bash
./download.sh
```

### 2. Generación de Artefactos
Para compilar y preparar los archivos de configuración dinámicos:
```bash
./generate.sh
```

### 3. Proceso de Despliegue
Ejecuta el script automatizado para desplegar la infraestructura según el entorno objetivo:
```bash
./deploy.sh
```

### 4. Verificación y Control de Calidad
Dado que nos encontramos depurando activamente, es fundamental validar la integridad del sistema antes de cada commit mediante las herramientas de verificación:
```bash
python3 verify.py
node verify-portal.cjs
```

---

## 🐛 Fase Actual: Depuración y Testing

Nos encontramos puliendo los últimos detalles de rendimiento y estabilidad. Si vas a colaborar en esta fase, ten en cuenta las siguientes directrices:
* **Logs y Errores:** Registra cualquier anomalía detectada durante el arranque PXE (`usb/`) o en la interacción del portal (`src/`).
* **Pruebas Locales:** Utiliza `TESTING.md` como referencia para replicar escenarios de prueba controlados.
* **Aislamiento de Cambios:** No modifiques scripts centrales de producción (`deploy.sh`, `build.py`) sin haber validado su comportamiento previo en un entorno aislado.

---

## 🌿 Normas Git y Estándares de Representación Markdown

Para mantener el repositorio limpio, legible y profesional, seguimos estrictamente las siguientes normas de control de versiones y documentación:

### 🔀 Estrategia de Ramas (Branching Strategy)
* `main` / `master`: Contiene exclusivamente versiones estables, probadas y listas para producción. **Prohibido hacer commits directos.**
* `dev` / `staging`: Rama principal de integración para las tareas diarias.
* `feature/nombre-de-la-caracteristica`: Para nuevas funcionalidades o mejoras específicas.
* `bugfix/descripcion-del-error`: Dedicada de forma exclusiva a las tareas de depuración actuales.

### 💬 Convención de Mensajes de Commit
Utilizamos [Conventional Commits](https://www.conventionalcommits.org/) para estructurar los mensajes de forma clara:
* `feat:` Nueva característica o componente (ej. `feat(portal): añade soporte dinámico en portal.js`).
* `fix:` Corrección de un error o fallo de depuración (ej. `fix(usb): corrige parámetro de timeout en bootstrap.ipxe`).
* `docs:` Cambios o ampliaciones en la documentación (`README.md`, `TESTING.md`).
* `refactor:` Refactorización de código sin alterar su funcionalidad (`src/common.py`).
* `chore:` Actualización de tareas de mantenimiento, scripts de compilación o dependencias.

### 📝 Estándares de Documentación Markdown (`.md`)
* Uso obligatorio de encabezados jerárquicos estructurados (`#`, `##`, `###`).
* Inclusión de badges informativos en la cabecera para reflejar el estado del proyecto.
* Bloques de código con sintaxis explícitamente declarada (ej. ```bash, ```json, ```python).
* Tablas y listas limpias para mejorar la legibilidad visual en cualquier cliente Git (GitHub, GitLab, etc.).

---

## 👥 Contribución y Agradecimientos

Este proyecto refleja el esfuerzo colaborativo y el ingenio de nuestra madre al timón del desarrollo. ¡Toda ayuda en la depuración es bienvenida! 

1. Realiza un *Fork* del repositorio.
2. Crea tu rama de trabajo (`git checkout -b bugfix/nombre-depuracion`).
3. Realiza tus cambios siguiendo las normas de commit.
4. Envía un *Pull Request* detallando las pruebas realizadas.

---
<div align="center">
  <sub>Desarrollado con dedicación, café y mucho espíritu de mejora continua. 🛠️✨</sub>
</div>
