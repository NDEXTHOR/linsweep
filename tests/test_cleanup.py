from pathlib import Path

import linsweep.modules.cleanup as cleanup
from linsweep.models import CachedPackage, PackageStatus


def make_package(
    name: str,
    status: PackageStatus,
    size: int = 1024,
) -> CachedPackage:
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


def test_cleanup_candidates_only_old_and_not_installed(
    monkeypatch,
) -> None:
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

    candidates = (
        cleanup.get_pacman_cleanup_candidates()
    )

    assert len(candidates) == 2

    statuses = {
        package.status
        for package in candidates
    }

    assert statuses == {
        PackageStatus.OLD,
        PackageStatus.NOT_INSTALLED,
    }


def test_cleanup_candidates_sorted_by_size(
    monkeypatch,
) -> None:
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

    candidates = (
        cleanup.get_pacman_cleanup_candidates()
    )

    assert [
        package.name
        for package in candidates
    ] == [
        "large",
        "medium",
        "small",
    ]


def test_execute_cleanup_requires_paccache(
    monkeypatch,
) -> None:
    def fake_which(command: str):
        if command == "paccache":
            return None

        return f"/usr/bin/{command}"

    monkeypatch.setattr(
        cleanup.shutil,
        "which",
        fake_which,
    )

    success, message = (
        cleanup.execute_pacman_cleanup()
    )

    assert success is False
    assert "paccache" in message


def test_execute_cleanup_runs_expected_commands(
    monkeypatch,
) -> None:
    commands = []

    class FakeResult:
        returncode = 0

    def fake_run(
        command,
        check=False,
    ):
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

    success, message = (
        cleanup.execute_pacman_cleanup()
    )

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

    assert (
        "completada"
        in message.lower()
    )


def test_execute_cleanup_stops_on_error(
    monkeypatch,
) -> None:
    commands = []

    class FakeResult:
        def __init__(
            self,
            returncode: int,
        ):
            self.returncode = returncode

    def fake_run(
        command,
        check=False,
    ):
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

    success, message = (
        cleanup.execute_pacman_cleanup()
    )

    assert success is False

    assert len(commands) == 1

    assert (
        "error"
        in message.lower()
        or "interrumpida"
        in message.lower()
    )
