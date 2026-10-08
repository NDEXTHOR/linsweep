# Changelog

Todos los cambios importantes de LinSweep se documentarán en este archivo.

El proyecto sigue una estructura inspirada en Keep a Changelog.

## [Sin publicar]

### Añadido

- Analizador de caché de Pacman.
- Clasificación de paquetes almacenados por versión.
- Detección de versiones instaladas, de respaldo, antiguas y más nuevas.
- Detección de paquetes que ya no están instalados.
- Cálculo de espacio potencialmente recuperable en Pacman.
- Analizador de systemd journal.
- Analizador de caché de Yay / AUR.
- Clasificación de paquetes compilados y fuentes descargadas de Yay.
- Analizador inicial de caché de usuario.
- Subcomandos de línea de comandos:
  - `packages`
  - `journal`
  - `yay`
  - `cache`
- Soporte para `--details` en módulos compatibles.

### En desarrollo

- Clasificación de cachés de usuario según nivel de riesgo.
- Análisis especializado de cachés de JetBrains.
- Limpieza segura con confirmación.
- Modo `dry-run`.
