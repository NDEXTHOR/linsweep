from pathlib import Path

from linsweep.models import CleanupCandidate, RiskLevel


USER_CACHE = Path.home() / ".cache"


MANAGED_CACHES = {
    "yay",
}


SAFE_CACHES = {
    "mozilla": (
        "Caché de Firefox. Es reconstruible, "
        "pero conviene limpiarla con Firefox cerrado."
    ),
    "fontconfig": (
        "Caché de fuentes. Se puede reconstruir."
    ),
    "wallust": (
        "Caché generada por Wallust."
    ),
    "mesa_shader_cache": (
        "Caché de shaders de Mesa."
    ),
    "radv_builtin_shaders": (
        "Caché de shaders de RADV."
    ),
    "thumbnails": (
        "Miniaturas generadas por aplicaciones."
    ),
    "pip": (
        "Caché de paquetes descargados por pip."
    ),
    "gstreamer-1.0": (
        "Caché generada por GStreamer."
    ),
}


REVIEW_CACHES = {
    "JetBrains": (
        "Caché de IDEs JetBrains. Puede contener índices, "
        "plugins descargados, logs y otros datos útiles."
    ),
    "vscode-cpptools": (
        "Datos de caché de la extensión C/C++ de VS Code."
    ),
    "Proton": (
        "Caché relacionada con Proton. Revisar antes de limpiar."
    ),
    "cliphist": (
        "Puede contener historial del portapapeles."
    ),
    "virt-manager": (
        "Caché de virt-manager. Revisar antes de limpiar."
    ),
    "copilot": (
        "Caché relacionada con Copilot. Revisar antes de limpiar."
    ),
}


def get_directory_size(path: Path) -> int:
    total = 0

    if not path.exists():
        return 0

    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue

    return total


def classify_cache(
    name: str,
) -> tuple[RiskLevel, str]:
    if name in SAFE_CACHES:
        return (
            RiskLevel.SAFE,
            SAFE_CACHES[name],
        )

    if name in REVIEW_CACHES:
        return (
            RiskLevel.REVIEW,
            REVIEW_CACHES[name],
        )

    return (
        RiskLevel.UNKNOWN,
        "Caché no reconocida todavía por LinSweep.",
    )


def scan_user_cache() -> list[CleanupCandidate]:
    entries: list[CleanupCandidate] = []

    if not USER_CACHE.exists():
        return entries

    try:
        items = USER_CACHE.iterdir()
    except PermissionError:
        return entries

    for path in items:
        if not path.is_dir():
            continue

        if path.name in MANAGED_CACHES:
            continue

        risk, description = classify_cache(
            path.name
        )

        entries.append(
            CleanupCandidate(
                name=path.name,
                path=path,
                size_bytes=get_directory_size(path),
                description=description,
                risk=risk,
            )
        )

    return entries
