import shutil
import subprocess

from linsweep.models import CachedPackage, PackageStatus
from linsweep.modules.pacman import (
    classify_packages,
    scan_pacman_cache,
)


def get_pacman_cleanup_candidates() -> list[CachedPackage]:
    packages = classify_packages(
        scan_pacman_cache()
    )

    candidates = [
        package
        for package in packages
        if package.status in (
            PackageStatus.OLD,
            PackageStatus.NOT_INSTALLED,
        )
    ]

    candidates.sort(
        key=lambda package: package.size_bytes,
        reverse=True,
    )

    return candidates


def execute_pacman_cleanup() -> tuple[bool, str]:
    if shutil.which("paccache") is None:
        return (
            False,
            "No se encontró paccache. "
            "Instala pacman-contrib para continuar.",
        )

    if shutil.which("sudo") is None:
        return (
            False,
            "No se encontró sudo.",
        )

    commands = [
        [
            "sudo",
            "paccache",
            "-r",
            "-k",
            "2",
        ],
        [
            "sudo",
            "paccache",
            "-r",
            "-u",
            "-k",
            "0",
        ],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            check=False,
        )

        if result.returncode != 0:
            return (
                False,
                "La limpieza fue interrumpida "
                "o paccache devolvió un error.",
            )

    return (
        True,
        "Limpieza de caché de Pacman completada.",
    )
