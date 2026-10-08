from dataclasses import dataclass
from pathlib import Path


DEFAULT_MIN_SIZE = 500 * 1024 * 1024

EXCLUDED_DIRECTORIES = {
    ".cache",
    ".local/share/Trash",
}


@dataclass
class LargeFile:
    path: Path
    size_bytes: int


def should_exclude(path: Path, home: Path) -> bool:
    try:
        relative = path.relative_to(home)
    except ValueError:
        return False

    relative_str = str(relative)

    for excluded in EXCLUDED_DIRECTORIES:
        if relative_str == excluded:
            return True

        if relative_str.startswith(excluded + "/"):
            return True

    return False


def scan_large_files(
    root: Path | None = None,
    min_size: int = DEFAULT_MIN_SIZE,
) -> list[LargeFile]:
    if root is None:
        root = Path.home()

    results: list[LargeFile] = []

    if not root.exists():
        return results

    for path in root.rglob("*"):
        try:
            if path.is_symlink():
                continue

            if should_exclude(path, root):
                continue

            if not path.is_file():
                continue

            size = path.stat().st_size

            if size >= min_size:
                results.append(
                    LargeFile(
                        path=path,
                        size_bytes=size,
                    )
                )

        except (
            PermissionError,
            OSError,
        ):
            continue

    results.sort(
        key=lambda item: item.size_bytes,
        reverse=True,
    )

    return results
