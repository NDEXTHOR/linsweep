from pathlib import Path

from linsweep.models import YayCacheEntry
from linsweep.modules.pacman import (
    compare_versions,
    get_installed_packages,
    parse_package_filename,
)


YAY_CACHE = Path.home() / ".cache" / "yay"


SOURCE_EXTENSIONS = (
    ".deb",
    ".rpm",
    ".zip",
    ".7z",
    ".tar.gz",
    ".tar.xz",
    ".tar.bz2",
    ".tar.zst",
    ".tgz",
    ".txz",
)


METADATA_FILES = {
    "PKGBUILD",
    ".SRCINFO",
    ".gitignore",
    ".nvchecker.toml",
}


def get_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


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


def is_compiled_package(path: Path) -> bool:
    return (
        path.is_file()
        and ".pkg.tar." in path.name
        and not path.name.endswith(".sig")
    )


def is_downloaded_source(path: Path) -> bool:
    name = path.name.lower()

    return any(
        name.endswith(extension)
        for extension in SOURCE_EXTENSIONS
    )


def is_metadata_file(path: Path) -> bool:
    if path.name in METADATA_FILES:
        return True

    if path.name.endswith(".install"):
        return True

    return False


def scan_yay_cache() -> list[YayCacheEntry]:
    entries: list[YayCacheEntry] = []

    if not YAY_CACHE.exists():
        return entries

    installed = get_installed_packages()

    for package_dir in YAY_CACHE.iterdir():

        if not package_dir.is_dir():
            continue

        total_size = get_directory_size(package_dir)

        compiled_current_size = 0
        compiled_old_size = 0
        compiled_newer_size = 0
        compiled_not_installed_size = 0

        compiled_current_count = 0
        compiled_old_count = 0
        compiled_newer_count = 0
        compiled_not_installed_count = 0

        downloaded_sources_size = 0
        metadata_size = 0

        git_dir = package_dir / ".git"
        git_size = get_directory_size(git_dir)

        for item in package_dir.iterdir():

            if item.name == ".git":
                continue

            if not item.is_file():
                continue

            size = get_file_size(item)

            if is_compiled_package(item):

                package = parse_package_filename(item)

                if package is None:
                    continue

                installed_version = installed.get(
                    package.name
                )

                if installed_version is None:
                    compiled_not_installed_size += size
                    compiled_not_installed_count += 1
                    continue

                comparison = compare_versions(
                    package.version,
                    installed_version,
                )

                if comparison == 0:
                    compiled_current_size += size
                    compiled_current_count += 1

                elif comparison < 0:
                    compiled_old_size += size
                    compiled_old_count += 1

                else:
                    compiled_newer_size += size
                    compiled_newer_count += 1

                continue

            if is_downloaded_source(item):
                downloaded_sources_size += size
                continue

            if is_metadata_file(item):
                metadata_size += size
                continue

        known_size = (
            compiled_current_size
            + compiled_old_size
            + compiled_newer_size
            + compiled_not_installed_size
            + downloaded_sources_size
            + git_size
            + metadata_size
        )

        other_size = max(
            0,
            total_size - known_size,
        )

        entries.append(
            YayCacheEntry(
                name=package_dir.name,
                path=package_dir,
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
            )
        )

    return entries
