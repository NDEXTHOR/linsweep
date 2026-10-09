from pathlib import Path

import linsweep.modules.cleanup as cleanup
from linsweep.models import (
    CachedPackage,
    CleanupCandidate,
    PackageStatus,
    RiskLevel,
    YayCacheEntry,
)

def make_package(name: str, status: PackageStatus, size: int = 1024) -> CachedPackage:
    return CachedPackage(
        name=name,
        version="1.0-1",
        architecture="x86_64",
        path=Path(
            f"/var/cache/pacman/pkg/"
            f"{name}-1.0-1-x86_64.pkg.tar.zst"
        ),
        size_bytes=size,
        status=status,
    )


def test_cleanup_candidates_only_old_and_not_installed(monkeypatch) -> None:
    packages = [
        make_package(
            "installed",
            PackageStatus.INSTALLED,
        ),
        make_package(
            "backup",
            PackageStatus.BACKUP,
        ),
        make_package(
            "old",
            PackageStatus.OLD,
        ),
        make_package(
            "unused",
            PackageStatus.NOT_INSTALLED,
        ),
        make_package(
            "newer",
            PackageStatus.NEWER,
        ),
    ]

    monkeypatch.setattr(
        cleanup,
        "scan_pacman_cache",
        lambda: packages,
    )

    monkeypatch.setattr(
        cleanup,
        "classify_packages",
        lambda items: items,
    )

    candidates = cleanup.get_pacman_cleanup_candidates()

    assert len(candidates) == 2

    statuses = {
        package.status
        for package in candidates
    }

    assert statuses == {
        PackageStatus.OLD,
        PackageStatus.NOT_INSTALLED,
    }


def test_cleanup_candidates_sorted_by_size(monkeypatch) -> None:
    packages = [
        make_package(
            "small",
            PackageStatus.OLD,
            1024,
        ),
        make_package(
            "large",
            PackageStatus.NOT_INSTALLED,
            4096,
        ),
        make_package(
            "medium",
            PackageStatus.OLD,
            2048,
        ),
    ]

    monkeypatch.setattr(
        cleanup,
        "scan_pacman_cache",
        lambda: packages,
    )

    monkeypatch.setattr(
        cleanup,
        "classify_packages",
        lambda items: items,
    )

    candidates = cleanup.get_pacman_cleanup_candidates()

    assert [
        package.name
        for package in candidates
    ] == [
        "large",
        "medium",
        "small",
    ]


def test_execute_cleanup_requires_paccache(monkeypatch) -> None:
    def fake_which(command: str):
        if command == "paccache":
            return None

        return f"/usr/bin/{command}"

    monkeypatch.setattr(
        cleanup.shutil,
        "which",
        fake_which,
    )

    success, message = cleanup.execute_pacman_cleanup()

    assert success is False
    assert "paccache" in message


def test_execute_cleanup_runs_expected_commands(monkeypatch) -> None:
    commands = []

    class FakeResult:
        returncode = 0

    def fake_run(command, check=False):
        commands.append(command)
        return FakeResult()

    monkeypatch.setattr(
        cleanup.shutil,
        "which",
        lambda command: f"/usr/bin/{command}",
    )

    monkeypatch.setattr(
        cleanup.subprocess,
        "run",
        fake_run,
    )

    success, message = cleanup.execute_pacman_cleanup()

    assert success is True

    assert commands == [
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

    assert "completada" in message.lower()


def test_execute_cleanup_stops_on_error(monkeypatch) -> None:
    commands = []

    class FakeResult:
        def __init__(self, returncode: int):
            self.returncode = returncode

    def fake_run(command, check=False):
        commands.append(command)
        return FakeResult(1)

    monkeypatch.setattr(
        cleanup.shutil,
        "which",
        lambda command: f"/usr/bin/{command}",
    )

    monkeypatch.setattr(
        cleanup.subprocess,
        "run",
        fake_run,
    )

    success, message = cleanup.execute_pacman_cleanup()

    assert success is False
    assert len(commands) == 1

    assert (
        "error" in message.lower()
        or "interrumpida" in message.lower()
    )


def test_get_trash_cleanup_candidates(monkeypatch) -> None:
    entries = [
        cleanup.TrashEntry(
            name="example.txt",
            path=Path("/tmp/example.txt"),
            size_bytes=1024,
        )
    ]

    monkeypatch.setattr(
        cleanup,
        "scan_trash",
        lambda: entries,
    )

    result = cleanup.get_trash_cleanup_candidates()

    assert result == entries


def test_execute_trash_cleanup_removes_file_and_metadata(tmp_path: Path, monkeypatch) -> None:
    trash_directory = tmp_path / "Trash"
    files_directory = trash_directory / "files"
    info_directory = trash_directory / "info"

    files_directory.mkdir(parents=True)
    info_directory.mkdir(parents=True)

    file_path = files_directory / "example.txt"

    file_path.write_text(
        "LinSweep",
        encoding="utf-8",
    )

    info_path = info_directory / "example.txt.trashinfo"

    info_path.write_text(
        "[Trash Info]\n"
        "Path=/home/user/example.txt\n",
        encoding="utf-8",
    )

    entry = cleanup.TrashEntry(
        name="example.txt",
        path=file_path,
        size_bytes=file_path.stat().st_size,
    )

    monkeypatch.setattr(
        cleanup,
        "get_trash_directory",
        lambda: trash_directory,
    )

    success, deleted_count, message = cleanup.execute_trash_cleanup(
        [entry]
    )

    assert success is True
    assert deleted_count == 1
    assert not file_path.exists()
    assert not info_path.exists()
    assert "correctamente" in message.lower()


def test_execute_trash_cleanup_removes_directory(tmp_path: Path, monkeypatch) -> None:
    trash_directory = tmp_path / "Trash"
    files_directory = trash_directory / "files"
    info_directory = trash_directory / "info"

    directory = files_directory / "folder"
    directory.mkdir(parents=True)

    info_directory.mkdir(parents=True)

    nested_file = directory / "example.txt"

    nested_file.write_text(
        "LinSweep",
        encoding="utf-8",
    )

    info_path = info_directory / "folder.trashinfo"

    info_path.write_text(
        "[Trash Info]\n"
        "Path=/home/user/folder\n",
        encoding="utf-8",
    )

    entry = cleanup.TrashEntry(
        name="folder",
        path=directory,
        size_bytes=nested_file.stat().st_size,
    )

    monkeypatch.setattr(
        cleanup,
        "get_trash_directory",
        lambda: trash_directory,
    )

    success, deleted_count, _ = cleanup.execute_trash_cleanup(
        [entry]
    )

    assert success is True
    assert deleted_count == 1
    assert not directory.exists()
    assert not info_path.exists()


def test_execute_trash_cleanup_rejects_path_outside_trash(tmp_path: Path, monkeypatch) -> None:
    trash_directory = tmp_path / "Trash"

    (trash_directory / "files").mkdir(
        parents=True
    )

    outside_file = tmp_path / "important.txt"

    outside_file.write_text(
        "No borrar",
        encoding="utf-8",
    )

    entry = cleanup.TrashEntry(
        name="important.txt",
        path=outside_file,
        size_bytes=outside_file.stat().st_size,
    )

    monkeypatch.setattr(
        cleanup,
        "get_trash_directory",
        lambda: trash_directory,
    )

    success, deleted_count, message = cleanup.execute_trash_cleanup(
        [entry]
    )

    assert success is False
    assert deleted_count == 0
    assert outside_file.exists()
    assert "fuera" in message.lower()

def test_get_yay_cleanup_candidates_returns_downloaded_sources(tmp_path: Path, monkeypatch) -> None:
    source_file = tmp_path / "source.tar.gz"
    source_file.write_bytes(b"x" * 2048)

    entry = YayCacheEntry(
        name="example",
        path=tmp_path,
        total_size=2048,
        downloaded_sources_size=2048,
        downloaded_source_paths=[
            source_file,
        ],
    )

    monkeypatch.setattr(
        cleanup,
        "scan_yay_cache",
        lambda: [entry],
    )

    candidates = cleanup.get_yay_cleanup_candidates()

    assert len(candidates) == 1
    assert candidates[0].path == source_file
    assert candidates[0].size_bytes == 2048
    assert candidates[0].risk == cleanup.RiskLevel.SAFE


def test_execute_yay_cleanup_removes_downloaded_source(tmp_path: Path, monkeypatch) -> None:
    yay_cache = tmp_path / "yay"
    package_directory = yay_cache / "example"

    package_directory.mkdir(
        parents=True
    )

    source_file = package_directory / "source.tar.gz"

    source_file.write_text(
        "LinSweep",
        encoding="utf-8",
    )

    candidate = cleanup.CleanupCandidate(
        name=source_file.name,
        path=source_file,
        size_bytes=source_file.stat().st_size,
        description="Fuente descargada por Yay.",
        risk=cleanup.RiskLevel.SAFE,
    )

    monkeypatch.setattr(
        cleanup,
        "YAY_CACHE",
        yay_cache,
    )

    success, deleted_count, message = cleanup.execute_yay_cleanup(
        [candidate]
    )

    assert success is True
    assert deleted_count == 1
    assert not source_file.exists()
    assert "completada" in message.lower()


def test_execute_yay_cleanup_rejects_path_outside_cache(tmp_path: Path, monkeypatch) -> None:
    yay_cache = tmp_path / "yay"

    yay_cache.mkdir()

    outside_file = tmp_path / "important.txt"

    outside_file.write_text(
        "No borrar",
        encoding="utf-8",
    )

    candidate = cleanup.CleanupCandidate(
        name=outside_file.name,
        path=outside_file,
        size_bytes=outside_file.stat().st_size,
        description="Prueba",
        risk=cleanup.RiskLevel.SAFE,
    )

    monkeypatch.setattr(
        cleanup,
        "YAY_CACHE",
        yay_cache,
    )

    success, deleted_count, message = cleanup.execute_yay_cleanup(
        [candidate]
    )

    assert success is False
    assert deleted_count == 0
    assert outside_file.exists()
    assert "fuera" in message.lower()


def test_execute_yay_cleanup_unlinks_symlink_without_deleting_target(tmp_path: Path, monkeypatch) -> None:
    yay_cache = tmp_path / "yay"
    package_directory = yay_cache / "example"

    package_directory.mkdir(
        parents=True
    )

    target_file = tmp_path / "important.txt"

    target_file.write_text(
        "No borrar",
        encoding="utf-8",
    )

    symlink = package_directory / "source.tar.gz"

    symlink.symlink_to(
        target_file
    )

    candidate = cleanup.CleanupCandidate(
        name=symlink.name,
        path=symlink,
        size_bytes=0,
        description="Prueba",
        risk=cleanup.RiskLevel.SAFE,
    )

    monkeypatch.setattr(
        cleanup,
        "YAY_CACHE",
        yay_cache,
    )

    success, deleted_count, _ = cleanup.execute_yay_cleanup(
        [candidate]
    )

    assert success is True
    assert deleted_count == 1
    assert not symlink.exists()
    assert target_file.exists()

def test_user_cache_cleanup_candidates_separates_available_and_in_use(tmp_path: Path, monkeypatch) -> None:
    cache_root = tmp_path / ".cache"
    cache_root.mkdir()

    available_path = cache_root / "available"
    in_use_path = cache_root / "in-use"
    review_path = cache_root / "review"
    symlink_path = cache_root / "symlink"

    available_path.mkdir()
    in_use_path.mkdir()
    review_path.mkdir()

    open_file = in_use_path / "cache.bin"
    open_file.write_text(
        "en uso",
        encoding="utf-8",
    )

    symlink_target = tmp_path / "target"
    symlink_target.mkdir()

    symlink_path.symlink_to(
        symlink_target,
        target_is_directory=True,
    )

    entries = [
        CleanupCandidate(
            name="available",
            path=available_path,
            size_bytes=100,
            description="Prueba.",
            risk=RiskLevel.SAFE,
        ),
        CleanupCandidate(
            name="in-use",
            path=in_use_path,
            size_bytes=200,
            description="Prueba.",
            risk=RiskLevel.SAFE,
        ),
        CleanupCandidate(
            name="review",
            path=review_path,
            size_bytes=300,
            description="Prueba.",
            risk=RiskLevel.REVIEW,
        ),
        CleanupCandidate(
            name="symlink",
            path=symlink_path,
            size_bytes=400,
            description="Prueba.",
            risk=RiskLevel.SAFE,
        ),
    ]

    monkeypatch.setattr(
        cleanup,
        "USER_CACHE",
        cache_root,
    )

    monkeypatch.setattr(
        cleanup,
        "scan_user_cache",
        lambda: entries,
    )

    monkeypatch.setattr(
        cleanup,
        "get_user_process_paths",
        lambda: {
            open_file.resolve(),
        },
    )

    candidates, in_use, blocked = cleanup.get_user_cache_cleanup_candidates()

    assert [
        candidate.name
        for candidate in candidates
    ] == [
        "available",
    ]

    assert [
        candidate.name
        for candidate in in_use
    ] == [
        "in-use",
    ]

    assert [
        candidate.name
        for candidate in blocked
    ] == [
        "symlink",
    ]


def test_execute_user_cache_cleanup_removes_safe_directory(tmp_path: Path, monkeypatch) -> None:
    cache_root = tmp_path / ".cache"
    cache_path = cache_root / "example"

    cache_path.mkdir(
        parents=True
    )

    cached_file = cache_path / "cache.bin"
    cached_file.write_bytes(
        b"x" * 1024
    )

    candidate = CleanupCandidate(
        name="example",
        path=cache_path,
        size_bytes=1024,
        description="Prueba.",
        risk=RiskLevel.SAFE,
    )

    monkeypatch.setattr(
        cleanup,
        "USER_CACHE",
        cache_root,
    )

    monkeypatch.setattr(
        cleanup,
        "get_user_process_paths",
        lambda: set(),
    )

    success, deleted_count, deleted_size, message = cleanup.execute_user_cache_cleanup(
        [candidate]
    )

    assert success is True
    assert deleted_count == 1
    assert deleted_size == 1024
    assert not cache_path.exists()
    assert "completada" in message.lower()


def test_execute_user_cache_cleanup_rejects_non_safe_candidate(tmp_path: Path, monkeypatch) -> None:
    cache_root = tmp_path / ".cache"
    cache_path = cache_root / "important"

    cache_path.mkdir(
        parents=True
    )

    candidate = CleanupCandidate(
        name="important",
        path=cache_path,
        size_bytes=1024,
        description="Prueba.",
        risk=RiskLevel.REVIEW,
    )

    monkeypatch.setattr(
        cleanup,
        "USER_CACHE",
        cache_root,
    )

    monkeypatch.setattr(
        cleanup,
        "get_user_process_paths",
        lambda: set(),
    )

    success, deleted_count, deleted_size, message = cleanup.execute_user_cache_cleanup(
        [candidate]
    )

    assert success is False
    assert deleted_count == 0
    assert deleted_size == 0
    assert cache_path.exists()
    assert "safe" in message.lower()


def test_execute_user_cache_cleanup_rejects_path_outside_cache(tmp_path: Path, monkeypatch) -> None:
    cache_root = tmp_path / ".cache"
    cache_root.mkdir()

    outside_path = tmp_path / "important"

    outside_path.mkdir()

    candidate = CleanupCandidate(
        name="important",
        path=outside_path,
        size_bytes=1024,
        description="Prueba.",
        risk=RiskLevel.SAFE,
    )

    monkeypatch.setattr(
        cleanup,
        "USER_CACHE",
        cache_root,
    )

    monkeypatch.setattr(
        cleanup,
        "get_user_process_paths",
        lambda: set(),
    )

    success, deleted_count, deleted_size, message = cleanup.execute_user_cache_cleanup(
        [candidate]
    )

    assert success is False
    assert deleted_count == 0
    assert deleted_size == 0
    assert outside_path.exists()
    assert "fuera" in message.lower()


def test_execute_user_cache_cleanup_rejects_cache_in_use(tmp_path: Path, monkeypatch) -> None:
    cache_root = tmp_path / ".cache"
    cache_path = cache_root / "example"

    cache_path.mkdir(
        parents=True
    )

    open_file = cache_path / "cache.bin"

    open_file.write_text(
        "en uso",
        encoding="utf-8",
    )

    candidate = CleanupCandidate(
        name="example",
        path=cache_path,
        size_bytes=open_file.stat().st_size,
        description="Prueba.",
        risk=RiskLevel.SAFE,
    )

    monkeypatch.setattr(
        cleanup,
        "USER_CACHE",
        cache_root,
    )

    monkeypatch.setattr(
        cleanup,
        "get_user_process_paths",
        lambda: {
            open_file.resolve(),
        },
    )

    success, deleted_count, deleted_size, message = cleanup.execute_user_cache_cleanup(
        [candidate]
    )

    assert success is False
    assert deleted_count == 0
    assert deleted_size == 0
    assert cache_path.exists()
    assert "en uso" in message.lower()
