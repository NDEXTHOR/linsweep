from collections import defaultdict
from functools import cmp_to_key
from pathlib import Path
import subprocess

from linsweep.models import CachedPackage, PackageStatus


PACMAN_CACHE = Path("/var/cache/pacman/pkg")


def get_installed_packages() -> dict[str, str]:
    """
    Devuelve un diccionario con los paquetes instalados:

    {
        "linux": "7.2.8.arch1-2",
        "firefox": "...",
        ...
    }
    """

    try:
        result = subprocess.run(
            ["pacman", "-Q"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}

    installed: dict[str, str] = {}

    for line in result.stdout.splitlines():
        try:
            name, version = line.split(maxsplit=1)
        except ValueError:
            continue

        installed[name] = version

    return installed


def parse_package_filename(path: Path) -> CachedPackage | None:
    """
    Ejemplo:

    linux-7.2.8.arch1-2-x86_64.pkg.tar.zst

    se convierte en:

    name = linux
    version = 7.2.8.arch1-2
    architecture = x86_64
    """

    filename = path.name
    marker = ".pkg.tar."

    if marker not in filename:
        return None

    base = filename.split(marker, 1)[0]

    try:
        name, pkgver, pkgrel, architecture = base.rsplit("-", 3)
    except ValueError:
        return None

    version = f"{pkgver}-{pkgrel}"

    try:
        size = path.stat().st_size
    except OSError:
        return None

    return CachedPackage(
        name=name,
        version=version,
        architecture=architecture,
        path=path,
        size_bytes=size,
    )


def scan_pacman_cache() -> list[CachedPackage]:
    packages: list[CachedPackage] = []

    if not PACMAN_CACHE.exists():
        return packages

    try:
        entries = PACMAN_CACHE.iterdir()
    except PermissionError:
        return packages

    for path in entries:
        if not path.is_file():
            continue

        if path.suffix == ".sig":
            continue

        package = parse_package_filename(path)

        if package is not None:
            packages.append(package)

    return packages


def compare_versions(version_a: str, version_b: str) -> int:
    """
    Usa vercmp de Arch para comparar versiones correctamente.
    """

    try:
        result = subprocess.run(
            ["vercmp", version_a, version_b],
            capture_output=True,
            text=True,
            check=True,
        )

        return int(result.stdout.strip())

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        ValueError,
    ):
        return 0


def classify_packages(
    packages: list[CachedPackage],
) -> list[CachedPackage]:

    installed = get_installed_packages()

    grouped: dict[str, list[CachedPackage]] = defaultdict(list)

    for package in packages:
        grouped[package.name].append(package)

    for name, versions in grouped.items():

        versions.sort(
            key=cmp_to_key(
                lambda a, b: compare_versions(
                    b.version,
                    a.version,
                )
            )
        )

        installed_version = installed.get(name)

        # El paquete ya no está instalado.
        if installed_version is None:
            for package in versions:
                package.status = PackageStatus.NOT_INSTALLED

            continue

        backup_assigned = False

        for package in versions:

            if package.version == installed_version:
                package.status = PackageStatus.INSTALLED
                continue

            comparison = compare_versions(
                package.version,
                installed_version,
            )

            # Existe en caché una versión más nueva
            # que la actualmente instalada.
            if comparison > 0:
                package.status = PackageStatus.NEWER
                continue

            # Conservamos una versión anterior como respaldo.
            if not backup_assigned:
                package.status = PackageStatus.BACKUP
                backup_assigned = True
                continue

            package.status = PackageStatus.OLD

    return packages

