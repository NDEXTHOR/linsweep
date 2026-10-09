# LinSweep

LinSweep es una herramienta CLI de análisis y mantenimiento seguro para **Arch Linux**, diseñada para ayudar a identificar espacio recuperable y realizar tareas de limpieza sin eliminar archivos a ciegas.

Su principio es sencillo:

**Analizar → explicar → mostrar → usuario decide → ejecutar**

LinSweep intenta separar claramente el análisis de la eliminación. Antes de realizar una limpieza, muestra qué encontró, cuánto espacio está involucrado y qué elementos serían afectados.

> LinSweep está actualmente en desarrollo.

## Características

### Caché de Pacman

Analiza `/var/cache/pacman/pkg` y clasifica los paquetes almacenados según su relación con los paquetes actualmente instalados.

```bash
linsweep packages
linsweep packages --details
```

Puede identificar, entre otros:

- versiones actuales;
- versiones antiguas;
- paquetes que ya no están instalados;
- paquetes huérfanos instalados en el sistema.

La limpieza utiliza `paccache` en lugar de eliminar archivos directamente.

```bash
linsweep clean packages --dry-run
linsweep clean packages
```

---

### systemd journal

Muestra el espacio utilizado actualmente por `systemd-journald`.

```bash
linsweep journal
```

También puede reducir los journals archivados hasta aproximarse a un límite indicado por el usuario.

```bash
linsweep clean journal --max-size 100M --dry-run
linsweep clean journal --max-size 100M
```

LinSweep utiliza `journalctl --vacuum-size` y muestra la operación antes de ejecutarla.

---

### Caché de Yay / AUR

Analiza los directorios almacenados en:

```text
~/.cache/yay
```

y diferencia elementos como:

- paquetes compilados;
- versiones antiguas;
- fuentes descargadas;
- repositorios Git;
- metadatos.

```bash
linsweep yay
linsweep yay --details
```

La limpieza actual elimina únicamente fuentes descargadas seleccionadas como seguras.

```bash
linsweep clean yay --dry-run
linsweep clean yay
```

No elimina automáticamente paquetes compilados, repositorios Git ni metadatos AUR.

---

### Caché del usuario

Analiza los directorios dentro de:

```text
~/.cache
```

y los clasifica según el riesgo asociado a una posible limpieza.

```bash
linsweep cache
linsweep cache --details
```

LinSweep utiliza niveles de riesgo como:

- `SAFE`
- `REVIEW`
- `DANGEROUS`
- `UNKNOWN`

La limpieza automática solo considera entradas clasificadas como `SAFE`.

```bash
linsweep clean cache --dry-run
linsweep clean cache
```

Antes de eliminar una caché, LinSweep comprueba nuevamente que no esté siendo utilizada por procesos del usuario.

---

### Archivos grandes

Busca archivos que superen un tamaño determinado.

```bash
linsweep large-files
```

El tamaño mínimo predeterminado es de `500M`.

También puede indicarse otro límite:

```bash
linsweep large-files --min-size 1G
```

o analizar otra ruta:

```bash
linsweep large-files --path ~/Descargas --min-size 100M
```

Este módulo es únicamente de análisis y **nunca elimina archivos**.

---

### Papelera

Analiza la papelera del usuario y muestra cuánto espacio ocupa.

```bash
linsweep trash
linsweep trash --details
```

Puede mostrar previamente qué se eliminaría:

```bash
linsweep clean trash --dry-run
```

y posteriormente vaciarla:

```bash
linsweep clean trash
```

---

### Archivos temporales

Analiza archivos pertenecientes al usuario dentro de:

```text
/tmp
/var/tmp
```

```bash
linsweep temp
linsweep temp --details
```

Para la limpieza, LinSweep aplica varias comprobaciones antes de considerar un archivo candidato:

- debe pertenecer al usuario actual;
- debe ser un archivo regular;
- no puede ser un enlace simbólico;
- debe permanecer dentro de un directorio temporal permitido;
- debe superar la antigüedad mínima;
- no debe estar siendo utilizado por un proceso del usuario;
- archivos de coordinación como PID, locks, sockets o archivos de estado son bloqueados.

La antigüedad mínima predeterminada es de **7 días**.

```bash
linsweep clean temp --dry-run
```

Puede modificarse explícitamente:

```bash
linsweep clean temp --older-than 14 --dry-run
```

Para ejecutar la limpieza:

```bash
linsweep clean temp
```

Los archivos temporales permanecen clasificados como `REVIEW`, por lo que LinSweep muestra los candidatos y solicita confirmación antes de eliminarlos.

Además, las condiciones se vuelven a comprobar inmediatamente antes de cada eliminación.

---

## Modo dry-run

Las operaciones de limpieza soportan un modo de simulación:

```bash
--dry-run
```

Por ejemplo:

```bash
linsweep clean packages --dry-run
linsweep clean yay --dry-run
linsweep clean cache --dry-run
linsweep clean trash --dry-run
linsweep clean journal --max-size 100M --dry-run
linsweep clean temp --older-than 7 --dry-run
```

El modo `dry-run` muestra qué haría LinSweep sin modificar ningún archivo.

Es recomendable utilizarlo antes de una limpieza cuando se quiera revisar exactamente qué elementos serán afectados.

---

## Uso

Para ver los comandos disponibles:

```bash
linsweep --help
```

También puede consultarse la ayuda de cada comando:

```bash
linsweep packages --help
linsweep large-files --help
linsweep clean --help
linsweep clean temp --help
```

Ejecutar LinSweep sin argumentos:

```bash
linsweep
```

muestra un resumen general del sistema y de algunos de sus analizadores principales.

---

## Instalación para desarrollo

Clona el repositorio:

```bash
git clone https://github.com/NDEXTHOR/linsweep.git
cd linsweep
```

Crea un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instala LinSweep en modo editable:

```bash
pip install -e ".[dev]"
```

Después podrás utilizar:

```bash
linsweep
```

desde el entorno virtual.

---

## Pruebas

El proyecto utiliza `pytest`.

```bash
pytest -v
```

Actualmente LinSweep cuenta con pruebas para sus analizadores, selección de candidatos y operaciones de limpieza.

---

## Seguridad

LinSweep intenta seguir varias reglas:

1. **El análisis no requiere privilegios de root siempre que sea posible.**
2. **No se eliminan elementos desconocidos automáticamente.**
3. **Las operaciones muestran previamente qué elementos serán afectados.**
4. **Las limpiezas sensibles requieren confirmación explícita.**
5. **Las rutas y condiciones se vuelven a validar antes de eliminar archivos.**
6. **`--dry-run` permite inspeccionar las operaciones sin modificar el sistema.**
7. **Se prefieren herramientas oficiales del sistema, como `paccache` y `journalctl`, cuando existen.**

LinSweep no pretende decidir automáticamente qué debe eliminarse del sistema. Su objetivo es proporcionar información suficiente para que el usuario pueda tomar esa decisión.

---

## Estado del proyecto

LinSweep está desarrollado inicialmente para **Arch Linux**.

Actualmente incluye análisis de:

- caché de Pacman;
- paquetes huérfanos;
- systemd journal;
- caché de Yay/AUR;
- caché del usuario;
- archivos grandes;
- papelera;
- archivos temporales.

Y operaciones de limpieza para:

- caché antigua de Pacman;
- fuentes descargadas de Yay;
- cachés de usuario clasificadas como `SAFE`;
- papelera;
- journals archivados;
- archivos temporales antiguos.

---

## Roadmap

Algunas ideas para versiones futuras:

- mejorar la detección de archivos y directorios en uso;
- añadir nuevos analizadores;
- ampliar las clasificaciones de riesgo;
- mejorar los reportes de espacio recuperable;
- empaquetado para AUR;
- soporte para más distribuciones Linux;
- documentación adicional.

---

## Licencia

LinSweep se distribuye bajo la licencia MIT.

Copyright © 2026 Brayan Rios
