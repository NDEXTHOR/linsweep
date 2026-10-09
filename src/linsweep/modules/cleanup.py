import shutil
import subprocess

from linsweep.models import CachedPackage, PackageStatus
from linsweep.modules.pacman import (
    classify_packages,
    scan_pacman_cache,
)
from linsweep.modules.trash import (
    TrashEntry,
    get_trash_directory,
    scan_trash,
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


def get_trash_cleanup_candidates() -> list[TrashEntry]:
    return scan_trash()


def execute_trash_cleanup(
    entries: list[TrashEntry],
) -> tuple[bool, int, str]:
    trash_directory = get_trash_directory()

    files_directory = (
        trash_directory / "files"
    )

    info_directory = (
        trash_directory / "info"
    )

    try:
        files_root = files_directory.resolve(
            strict=False
        )
    except OSError:
        return (
            False,
            0,
            "No se pudo validar la ruta de la papelera.",
        )

    deleted_count = 0

    for entry in entries:
        path = entry.path

        # Las entradas que scan_trash() devuelve deben
        # encontrarse directamente dentro de Trash/files.
        try:
            parent = path.parent.resolve(
                strict=False
            )
        except OSError:
            return (
                False,
                deleted_count,
                f"No se pudo validar la ruta: {path}",
            )

        if parent != files_root:
            return (
                False,
                deleted_count,
                (
                    "Se rechazó una ruta fuera de "
                    f"la papelera: {path}"
                ),
            )

        try:
            if path.is_symlink():
                path.unlink()

            elif path.is_dir():
                shutil.rmtree(path)

            elif path.exists():
                path.unlink()

            else:
                # El elemento pudo desaparecer entre
                # el preview y la confirmación.
                continue

        except OSError as error:
            return (
                False,
                deleted_count,
                (
                    f"No se pudo eliminar {path}: "
                    f"{error}"
                ),
            )

        info_path = (
            info_directory
            / f"{path.name}.trashinfo"
        )

        try:
            if (
                info_path.is_file()
                or info_path.is_symlink()
            ):
                info_path.unlink()

        except OSError as error:
            return (
                False,
                deleted_count,
                (
                    "El elemento fue eliminado, "
                    "pero no se pudo borrar su "
                    f"metadato {info_path}: {error}"
                ),
            )

        deleted_count += 1

    return (
        True,
        deleted_count,
        "Papelera vaciada correctamente.",
    )
