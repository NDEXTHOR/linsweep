from collections import defaultdict
from functools import cmp_to_key
from pathlib import Path
import subprocess
import os
import re

from linsweep.models import (
    CachedPackage,
    OrphanPackage,
    PackageStatus,
)

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

def parse_installed_size(size_text: str) -> int:
    match = re.fullmatch(
        r"([\d.]+)\s*(B|KiB|MiB|GiB|TiB)",
        size_text.strip(),
        re.IGNORECASE,
    )

    if not match:
        return 0

    value = float(match.group(1))
    unit = match.group(2).lower()

    multipliers = {
        "b": 1,
        "kib": 1024,
        "mib": 1024 ** 2,
        "gib": 1024 ** 3,
        "tib": 1024 ** 4,
    }

    return int(
        value * multipliers[unit]
    )


def get_orphan_packages() -> list[OrphanPackage]:
    env = os.environ.copy()
    env["LC_ALL"] = "C"

    try:
        result = subprocess.run(
            ["pacman", "-Qdtq"],
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError:
        return []

    names = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if not names:
        return []

    try:
        info_result = subprocess.run(
            ["pacman", "-Qi", *names],
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError:
        return []

    orphans: list[OrphanPackage] = []

    for block in info_result.stdout.split("\n\n"):
        name = None
        version = None
        size_bytes = 0

        for line in block.splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            key = key.strip()
            value = value.strip()

            if key == "Name":
                name = value

            elif key == "Version":
                version = value

            elif key == "Installed Size":
                size_bytes = parse_installed_size(
                    value
                )

        if name and version:
            orphans.append(
                OrphanPackage(
                    name=name,
                    version=version,
                    size_bytes=size_bytes,
                )
            )

    orphans.sort(
        key=lambda package: package.size_bytes,
        reverse=True,
    )

    return orphans
