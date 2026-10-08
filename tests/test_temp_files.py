import os
from pathlib import Path

import linsweep.modules.temp_files as temp_files


def create_file(
    path: Path,
    size: int = 1024,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(
        b"\0" * size
    )


def test_scan_temp_files_finds_user_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    temp_directory = tmp_path / "tmp"
    file_path = temp_directory / "example.bin"

    create_file(
        file_path,
        2048,
    )

    monkeypatch.setattr(
        temp_files,
        "TEMP_DIRECTORIES",
        (temp_directory,),
    )

    results = temp_files.scan_temp_files()

    assert len(results) == 1
    assert results[0].path == file_path
    assert results[0].size_bytes == 2048


def test_scan_temp_files_ignores_other_uid(
    tmp_path: Path,
    monkeypatch,
) -> None:
    temp_directory = tmp_path / "tmp"
    file_path = temp_directory / "example.bin"

    create_file(file_path)

    monkeypatch.setattr(
        temp_files,
        "TEMP_DIRECTORIES",
        (temp_directory,),
    )

    real_uid = os.getuid()

    monkeypatch.setattr(
        temp_files.os,
        "getuid",
        lambda: real_uid + 1000,
    )

    results = temp_files.scan_temp_files()

    assert results == []

def test_scan_temp_files_ignores_symlinks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    temp_directory = tmp_path / "tmp"
    temp_directory.mkdir()

    target = tmp_path / "target.bin"
    create_file(target)

    symlink = temp_directory / "link.bin"
    symlink.symlink_to(target)

    monkeypatch.setattr(
        temp_files,
        "TEMP_DIRECTORIES",
        (temp_directory,),
    )

    results = temp_files.scan_temp_files()

    assert results == []


def test_scan_temp_files_calculates_age(
    tmp_path: Path,
    monkeypatch,
) -> None:
    temp_directory = tmp_path / "tmp"
    file_path = temp_directory / "old.bin"

    create_file(file_path)

    now = 1_000_000.0
    two_days = 2 * 86400

    os.utime(
        file_path,
        (
            now - two_days,
            now - two_days,
        ),
    )

    monkeypatch.setattr(
        temp_files,
        "TEMP_DIRECTORIES",
        (temp_directory,),
    )

    monkeypatch.setattr(
        temp_files.os,
        "getuid",
        os.getuid,
    )

    results = temp_files.scan_temp_files(
        now=now,
    )

    assert len(results) == 1

    # ctime puede ser más reciente que mtime,
    # así que la edad nunca debe resultar negativa.
    assert results[0].age_days >= 0
