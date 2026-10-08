# LinSweep

**LinSweep** es una herramienta modular de análisis y mantenimiento para **Arch Linux**.

Su objetivo es analizar el sistema, identificar espacio en disco potencialmente recuperable, clasificar las posibles acciones de limpieza según su riesgo y explicar al usuario qué puede eliminarse antes de realizar cualquier operación destructiva.

> **LinSweep se encuentra actualmente en desarrollo.**

## Filosofía

LinSweep sigue un principio sencillo:

> **Analizar primero. Explicar después. Limpiar solo con confirmación.**

La herramienta busca evitar limpiezas agresivas o la eliminación indiscriminada de archivos.

LinSweep no debería:

- Eliminar archivos desconocidos automáticamente.
- Realizar operaciones destructivas sin confirmación.
- Utilizar privilegios de administrador para tareas que no los necesitan.
- Considerar todo archivo de caché como innecesario.

Antes de realizar una limpieza, el objetivo es mostrar qué se encontró, cuánto espacio ocupa, qué función tiene y qué riesgo supondría eliminarlo.

## Funciones actuales

### Caché de Pacman

LinSweep puede analizar `/var/cache/pacman/pkg` y clasificar los paquetes almacenados como:

- Versión actualmente instalada.
- Versión de respaldo.
- Versión antigua.
- Versión más nueva que la instalada.
- Paquete que ya no está instalado.

También calcula cuánto espacio podría recuperarse eliminando versiones antiguas y paquetes que ya no se encuentran instalados.

### Systemd Journal

Permite consultar cuánto espacio están utilizando los registros de `systemd-journald` y estimar cuánto podría recuperarse estableciendo diferentes límites de almacenamiento.

Por ahora únicamente realiza análisis y no modifica los registros.

### Caché de Yay / AUR

LinSweep analiza `~/.cache/yay` y diferencia entre:

- Paquetes compilados correspondientes a la versión instalada.
- Paquetes compilados antiguos.
- Paquetes compilados más nuevos.
- Paquetes de software que ya no está instalado.
- Fuentes descargadas.
- Repositorios Git.
- Metadatos del AUR.
- Otros archivos.

Esto permite diferenciar archivos reconstruibles de información que puede resultar útil conservar.

### Caché de usuario

LinSweep puede analizar los directorios contenidos en:

```text
~/.cache
```

y mostrar qué aplicaciones están utilizando más espacio.

Este módulo se encuentra actualmente en desarrollo y posteriormente clasificará las cachés según su nivel de riesgo.

## Comandos disponibles

Mostrar un resumen general:

```bash
linsweep
```

Analizar la caché de Pacman:

```bash
linsweep packages
```

Mostrar los paquetes considerados antiguos o no instalados:

```bash
linsweep packages --details
```

Analizar `systemd journal`:

```bash
linsweep journal
```

Analizar la caché de Yay:

```bash
linsweep yay
```

Mostrar información detallada de la caché de Yay:

```bash
linsweep yay --details
```

Analizar la caché del usuario:

```bash
linsweep cache
```

Mostrar todos los directorios encontrados:

```bash
linsweep cache --details
```

## Instalación para desarrollo

Actualmente LinSweep todavía está en desarrollo y no cuenta con un paquete estable.

Clona el repositorio:

```bash
git clone <URL-DEL-REPOSITORIO>
cd linsweep
```

Crea un entorno virtual:

```bash
python -m venv .venv
```

Actívalo:

```bash
source .venv/bin/activate
```

Instala LinSweep en modo editable:

```bash
pip install -e .
```

Después puedes ejecutar:

```bash
linsweep
```

## Estructura del proyecto

```text
linsweep/
├── src/
│   └── linsweep/
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       └── modules/
│           ├── __init__.py
│           ├── journal.py
│           ├── pacman.py
│           ├── user_cache.py
│           └── yay.py
│
├── tests/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
└── pyproject.toml
```

## Funciones planeadas

LinSweep podrá incorporar posteriormente:

- Limpieza controlada de paquetes de Pacman.
- Limpieza de caché de Yay.
- Análisis avanzado de cachés de usuario.
- Detección de archivos grandes.
- Detección de archivos duplicados.
- Análisis de archivos temporales.
- Soporte para Docker.
- Soporte para libvirt/KVM.
- Análisis de máquinas virtuales y discos sin asociación.
- Modo `dry-run`.
- Confirmación antes de operaciones destructivas.
- Clasificación de acciones según riesgo.
- Interfaz TUI interactiva.
- Registro de operaciones realizadas.

## Compatibilidad

Actualmente el proyecto está enfocado en:

- Arch Linux
- Pacman
- systemd

Algunos módulos serán opcionales y se habilitarán únicamente cuando la herramienta correspondiente esté instalada, por ejemplo:

- Yay
- Docker
- libvirt

En el futuro podría estudiarse soporte para otras distribuciones Linux.

## Estado del proyecto

LinSweep se encuentra en una etapa temprana de desarrollo.

Actualmente los módulos se centran principalmente en **analizar y mostrar información**. Las operaciones de limpieza destructivas todavía no forman parte de la versión inicial.

Esto es intencional: primero se busca validar correctamente la detección y clasificación de archivos antes de permitir su eliminación.

## Licencia

Este proyecto se distribuirá bajo la licencia **MIT**.
