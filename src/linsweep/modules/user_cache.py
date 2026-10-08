from dataclasses import dataclass
from pathlib import Path


USER_CACHE = Path.home() / ".cache"

MANAGED_CACHES = {
    "yay",
}

@dataclass
class CacheDirectory:
    name: str
    path: Path
    size_bytes: int


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


def scan_user_cache() -> list[CacheDirectory]:
    entries: list[CacheDirectory] = []

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

        entries.append(
            CacheDirectory(
                name=path.name,
                path=path,
                size_bytes=get_directory_size(path),
            )
        )

    return entries
