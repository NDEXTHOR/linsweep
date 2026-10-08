import os
import time
from dataclasses import dataclass
from pathlib import Path


TEMP_DIRECTORIES = (
    Path("/tmp"),
    Path("/var/tmp"),
)


@dataclass
class TempFile:
    path: Path
    size_bytes: int
    age_days: float


def scan_temp_files(
    now: float | None = None,
) -> list[TempFile]:
    uid = os.getuid()

    current_time = (
        time.time()
        if now is None
        else now
    )

    results: list[TempFile] = []

    for root in TEMP_DIRECTORIES:
        if not root.exists():
            continue

        for dirpath, dirnames, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
            onerror=lambda _: None,
        ):
            base = Path(dirpath)

            # Evitar entrar en directorios que sean enlaces simbólicos.
            dirnames[:] = [
                name
                for name in dirnames
                if not (base / name).is_symlink()
            ]

            for filename in filenames:
                path = base / filename

                try:
                    if path.is_symlink():
                        continue

                    stat = path.stat()

                except (
                    PermissionError,
                    FileNotFoundError,
                    OSError,
                ):
                    continue

                # Analizar únicamente archivos pertenecientes
                # al usuario actual.
                if stat.st_uid != uid:
                    continue

                if not path.is_file():
                    continue

                # mtime puede conservar la fecha original de un archivo
                # copiado o extraído. Usamos la fecha más reciente entre
                # mtime y ctime para evitar clasificar como antiguo un
                # archivo temporal creado recientemente.
                activity_time = max(
                    stat.st_mtime,
                    stat.st_ctime,
                )

                age_seconds = max(
                    0,
                    current_time - activity_time,
                )

                results.append(
                    TempFile(
                        path=path,
                        size_bytes=stat.st_size,
                        age_days=(
                            age_seconds
                            / 86400
                        ),
                    )
                )

    results.sort(
        key=lambda item: item.age_days,
        reverse=True,
    )

    return results
