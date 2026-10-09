from pathlib import Path

from linsweep.models import PackageStatus, YayCacheEntry
from linsweep.modules.pacman import (
    compare_versions,
    get_installed_packages,
    parse_package_filename,
)


YAY_CACHE = Path.home() / ".cache" / "yay"


DOWNLOADED_SOURCE_EXTENSIONS = (
    ".tar",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tar.zst",
    ".tgz",
    ".tbz",
    ".tbz2",
    ".txz",
    ".zip",
    ".7z",
    ".rar",
    ".deb",
    ".rpm",
    ".AppImage",
)


METADATA_FILES = {
    "PKGBUILD",
    ".SRCINFO",
}


def get_path_size(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        return 0

    total = 0

    try:
        items = path.rglob("*")
    except OSError:
        return 0

    for item in items:
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue

    return total


def is_downloaded_source(path: Path) -> bool:
    if not path.is_file():
        return False

    name = path.name

    return any(
        name.endswith(extension)
        for extension in DOWNLOADED_SOURCE_EXTENSIONS
    )


def classify_compiled_package(package_name: str, package_version: str, installed: dict[str, str]) -> PackageStatus:
    installed_version = installed.get(package_name)

    if installed_version is None:
        return PackageStatus.NOT_INSTALLED

    comparison = compare_versions(
        package_version,
        installed_version,
    )

    if comparison == 0:
        return PackageStatus.INSTALLED

    if comparison < 0:
        return PackageStatus.OLD

    return PackageStatus.NEWER


def scan_yay_cache() -> list[YayCacheEntry]:
    entries: list[YayCacheEntry] = []

    if not YAY_CACHE.exists():
        return entries

    installed = get_installed_packages()

    try:
        package_directories = list(
            YAY_CACHE.iterdir()
        )
    except (PermissionError, OSError):
        return entries

    for package_directory in package_directories:
        if not package_directory.is_dir():
            continue

        total_size = get_path_size(
            package_directory
        )

        compiled_current_size = 0
        compiled_old_size = 0
        compiled_newer_size = 0
        compiled_not_installed_size = 0

        downloaded_sources_size = 0
        git_size = 0
        metadata_size = 0
        other_size = 0

        compiled_current_count = 0
        compiled_old_count = 0
        compiled_newer_count = 0
        compiled_not_installed_count = 0

        downloaded_source_paths: list[Path] = []

        try:
            items = list(
                package_directory.iterdir()
            )
        except (PermissionError, OSError):
            continue

        for item in items:
            try:
                size = get_path_size(item)
            except OSError:
                continue

            # Repositorio Git usado por Yay para el paquete AUR.
            if item.name == ".git" and item.is_dir():
                git_size += size
                continue

            # Archivos de metadatos del paquete AUR.
            if item.name in METADATA_FILES:
                metadata_size += size
                continue

            # Paquetes compilados (*.pkg.tar.*).
            if item.is_file():
                package = parse_package_filename(
                    item
                )

                if package is not None:
                    status = classify_compiled_package(
                        package.name,
                        package.version,
                        installed,
                    )

                    if status == PackageStatus.INSTALLED:
                        compiled_current_size += size
                        compiled_current_count += 1

                    elif status == PackageStatus.OLD:
                        compiled_old_size += size
                        compiled_old_count += 1

                    elif status == PackageStatus.NEWER:
                        compiled_newer_size += size
                        compiled_newer_count += 1

                    elif status == PackageStatus.NOT_INSTALLED:
                        compiled_not_installed_size += size
                        compiled_not_installed_count += 1

                    continue

            # Fuentes descargadas por Yay.
            if is_downloaded_source(item):
                downloaded_sources_size += size
                downloaded_source_paths.append(
                    item
                )
                continue

            # Cualquier otro archivo o directorio que
            # LinSweep todavía no clasifica.
            other_size += size

        entries.append(
            YayCacheEntry(
                name=package_directory.name,
                path=package_directory,
                total_size=total_size,
                compiled_current_size=compiled_current_size,
                compiled_old_size=compiled_old_size,
                compiled_newer_size=compiled_newer_size,
                compiled_not_installed_size=compiled_not_installed_size,
                downloaded_sources_size=downloaded_sources_size,
                git_size=git_size,
                metadata_size=metadata_size,
                other_size=other_size,
                compiled_current_count=compiled_current_count,
                compiled_old_count=compiled_old_count,
                compiled_newer_count=compiled_newer_count,
                compiled_not_installed_count=compiled_not_installed_count,
                downloaded_source_paths=downloaded_source_paths,
            )
        )

    entries.sort(
        key=lambda entry: entry.total_size,
        reverse=True,
    )

    return entries
