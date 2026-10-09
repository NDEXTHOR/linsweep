import os
import shutil
import subprocess
from pathlib import Path

from linsweep.models import (
    CachedPackage,
    CleanupCandidate,
    PackageStatus,
    RiskLevel,
)
from linsweep.modules.pacman import (
    classify_packages,
    scan_pacman_cache,
)
from linsweep.modules.trash import (
    TrashEntry,
    get_trash_directory,
    scan_trash,
)
from linsweep.modules.user_cache import (
    USER_CACHE,
    scan_user_cache,
)
from linsweep.modules.yay import (
    YAY_CACHE,
    scan_yay_cache,
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


def execute_trash_cleanup(entries: list[TrashEntry]) -> tuple[bool, int, str]:
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


def get_yay_cleanup_candidates() -> list[CleanupCandidate]:
    entries = scan_yay_cache()

    candidates: list[CleanupCandidate] = []

    for entry in entries:
        for path in entry.downloaded_source_paths:
            try:
                size = path.stat().st_size
            except OSError:
                continue

            candidates.append(
                CleanupCandidate(
                    name=path.name,
                    path=path,
                    size_bytes=size,
                    description="Fuente descargada por Yay.",
                    risk=RiskLevel.SAFE,
                )
            )

    candidates.sort(
        key=lambda candidate: candidate.size_bytes,
        reverse=True,
    )

    return candidates


def execute_yay_cleanup(candidates: list[CleanupCandidate]) -> tuple[bool, int, str]:
    try:
        yay_root = YAY_CACHE.resolve(
            strict=False
        )
    except OSError:
        return (
            False,
            0,
            "No se pudo validar la caché de Yay.",
        )

    deleted_count = 0

    for candidate in candidates:
        path = candidate.path

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

        if not parent.is_relative_to(yay_root):
            return (
                False,
                deleted_count,
                (
                    "Se rechazó una ruta fuera de "
                    f"la caché de Yay: {path}"
                ),
            )

        try:
            if (
                path.is_dir()
                and not path.is_symlink()
            ):
                return (
                    False,
                    deleted_count,
                    f"Se rechazó un directorio: {path}",
                )

            if (
                not path.exists()
                and not path.is_symlink()
            ):
                continue

            path.unlink()

        except OSError as error:
            return (
                False,
                deleted_count,
                f"No se pudo eliminar {path}: {error}",
            )

        deleted_count += 1

    return (
        True,
        deleted_count,
        "Limpieza de fuentes descargadas de Yay completada.",
    )


def normalize_process_path(raw_path: str) -> Path | None:
    if not raw_path.startswith("/"):
        return None

    if raw_path.endswith(" (deleted)"):
        raw_path = raw_path[:-10]

    try:
        return Path(raw_path).resolve(
            strict=False
        )
    except OSError:
        return None


def get_user_process_paths() -> set[Path]:
    paths: set[Path] = set()

    uid = os.getuid()
    proc_directory = Path("/proc")

    try:
        process_directories = list(
            proc_directory.iterdir()
        )
    except OSError:
        return paths

    for process_directory in process_directories:
        if not process_directory.name.isdigit():
            continue

        try:
            if process_directory.stat().st_uid != uid:
                continue
        except OSError:
            continue

        cwd_path = process_directory / "cwd"

        try:
            raw_path = os.readlink(
                cwd_path
            )
        except OSError:
            raw_path = ""

        normalized = normalize_process_path(
            raw_path
        )

        if normalized is not None:
            paths.add(normalized)

        fd_directory = (
            process_directory / "fd"
        )

        try:
            descriptors = list(
                fd_directory.iterdir()
            )
        except OSError:
            descriptors = []

        for descriptor in descriptors:
            try:
                raw_path = os.readlink(
                    descriptor
                )
            except OSError:
                continue

            normalized = normalize_process_path(
                raw_path
            )

            if normalized is not None:
                paths.add(normalized)

        maps_path = (
            process_directory / "maps"
        )

        try:
            maps_content = maps_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        for line in maps_content.splitlines():
            parts = line.split(
                maxsplit=5
            )

            if len(parts) < 6:
                continue

            raw_path = parts[5]

            normalized = normalize_process_path(
                raw_path
            )

            if normalized is not None:
                paths.add(normalized)

    return paths


def is_path_in_use(path: Path, process_paths: set[Path]) -> bool:
    try:
        target = path.resolve(
            strict=False
        )
    except OSError:
        return True

    for process_path in process_paths:
        if process_path == target:
            return True

        if target in process_path.parents:
            return True

    return False


def get_user_cache_cleanup_candidates() -> tuple[list[CleanupCandidate], list[CleanupCandidate], list[CleanupCandidate]]:
    entries = scan_user_cache()

    process_paths = get_user_process_paths()

    candidates: list[CleanupCandidate] = []
    in_use: list[CleanupCandidate] = []
    blocked: list[CleanupCandidate] = []

    for entry in entries:
        if entry.risk != RiskLevel.SAFE:
            continue

        if entry.path.is_symlink():
            blocked.append(entry)
            continue

        try:
            parent = entry.path.parent.resolve(
                strict=False
            )

            cache_root = USER_CACHE.resolve(
                strict=False
            )

        except OSError:
            blocked.append(entry)
            continue

        if parent != cache_root:
            blocked.append(entry)
            continue

        if is_path_in_use(
            entry.path,
            process_paths,
        ):
            in_use.append(entry)
            continue

        candidates.append(entry)

    candidates.sort(
        key=lambda candidate: candidate.size_bytes,
        reverse=True,
    )

    in_use.sort(
        key=lambda candidate: candidate.size_bytes,
        reverse=True,
    )

    blocked.sort(
        key=lambda candidate: candidate.size_bytes,
        reverse=True,
    )

    return (
        candidates,
        in_use,
        blocked,
    )


def execute_user_cache_cleanup(candidates: list[CleanupCandidate]) -> tuple[bool, int, int, str]:
    try:
        cache_root = USER_CACHE.resolve(
            strict=False
        )
    except OSError:
        return (
            False,
            0,
            0,
            "No se pudo validar la caché del usuario.",
        )

    process_paths = get_user_process_paths()

    for candidate in candidates:
        if candidate.risk != RiskLevel.SAFE:
            return (
                False,
                0,
                0,
                (
                    "Se rechazó un candidato que "
                    f"no es SAFE: {candidate.path}"
                ),
            )

        path = candidate.path

        if path.is_symlink():
            return (
                False,
                0,
                0,
                (
                    "Se rechazó un enlace simbólico: "
                    f"{path}"
                ),
            )

        try:
            parent = path.parent.resolve(
                strict=False
            )
        except OSError:
            return (
                False,
                0,
                0,
                f"No se pudo validar la ruta: {path}",
            )

        if parent != cache_root:
            return (
                False,
                0,
                0,
                (
                    "Se rechazó una ruta fuera de "
                    f"la caché del usuario: {path}"
                ),
            )

        if is_path_in_use(
            path,
            process_paths,
        ):
            return (
                False,
                0,
                0,
                (
                    "Se detectaron archivos en uso "
                    f"dentro de: {path}"
                ),
            )

    deleted_count = 0
    deleted_size = 0

    for candidate in candidates:
        path = candidate.path

        if not path.exists():
            continue

        try:
            if path.is_symlink():
                return (
                    False,
                    deleted_count,
                    deleted_size,
                    (
                        "La ruta cambió a un enlace "
                        f"simbólico: {path}"
                    ),
                )

            if path.is_dir():
                shutil.rmtree(path)

            elif path.is_file():
                path.unlink()

            else:
                return (
                    False,
                    deleted_count,
                    deleted_size,
                    (
                        "Se encontró un tipo de archivo "
                        f"no esperado: {path}"
                    ),
                )

        except OSError as error:
            return (
                False,
                deleted_count,
                deleted_size,
                f"No se pudo eliminar {path}: {error}",
            )

        deleted_count += 1
        deleted_size += candidate.size_bytes

    return (
        True,
        deleted_count,
        deleted_size,
        "Limpieza de caché del usuario completada.",
    )
