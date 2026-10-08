import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


@dataclass
class TrashEntry:
    name: str
    path: Path
    size_bytes: int
    original_path: str | None = None
    deletion_date: datetime | None = None


def get_trash_directory() -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")

    if xdg_data_home:
        return Path(xdg_data_home) / "Trash"

    return Path.home() / ".local" / "share" / "Trash"


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


def read_trash_info(
    info_path: Path,
) -> tuple[str | None, datetime | None]:
    original_path = None
    deletion_date = None

    try:
        content = info_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return original_path, deletion_date

    for line in content.splitlines():
        if line.startswith("Path="):
            original_path = unquote(
                line.removeprefix("Path=")
            )

        elif line.startswith("DeletionDate="):
            value = line.removeprefix(
                "DeletionDate="
            )

            try:
                deletion_date = datetime.fromisoformat(
                    value
                )
            except ValueError:
                pass

    return original_path, deletion_date


def scan_trash() -> list[TrashEntry]:
    trash = get_trash_directory()
    files_directory = trash / "files"
    info_directory = trash / "info"

    entries: list[TrashEntry] = []

    if not files_directory.exists():
        return entries

    try:
        items = files_directory.iterdir()
    except (PermissionError, OSError):
        return entries

    for path in items:
        info_path = (
            info_directory
            / f"{path.name}.trashinfo"
        )

        original_path = None
        deletion_date = None

        if info_path.exists():
            (
                original_path,
                deletion_date,
            ) = read_trash_info(info_path)

        entries.append(
            TrashEntry(
                name=path.name,
                path=path,
                size_bytes=get_path_size(path),
                original_path=original_path,
                deletion_date=deletion_date,
            )
        )

    entries.sort(
        key=lambda entry: entry.size_bytes,
        reverse=True,
    )

    return entries
