from pathlib import Path

import linsweep.modules.trash as trash


def create_file(
    path: Path,
    size: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(
        b"\0" * size
    )


def test_empty_trash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trash_directory = tmp_path / "Trash"
    files_directory = trash_directory / "files"

    files_directory.mkdir(
        parents=True
    )

    monkeypatch.setattr(
        trash,
        "get_trash_directory",
        lambda: trash_directory,
    )

    entries = trash.scan_trash()

    assert entries == []


def test_scan_trash_finds_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trash_directory = tmp_path / "Trash"
    files_directory = trash_directory / "files"

    create_file(
        files_directory / "example.bin",
        2048,
    )

    monkeypatch.setattr(
        trash,
        "get_trash_directory",
        lambda: trash_directory,
    )

    entries = trash.scan_trash()

    assert len(entries) == 1

    entry = entries[0]

    assert entry.name == "example.bin"
    assert entry.size_bytes == 2048


def test_read_trash_info(
    tmp_path: Path,
) -> None:
    info_file = tmp_path / "example.trashinfo"

    info_file.write_text(
        "[Trash Info]\n"
        "Path=/home/user/Descargas/example.txt\n"
        "DeletionDate=2026-10-08T12:30:00\n",
        encoding="utf-8",
    )

    original_path, deletion_date = (
        trash.read_trash_info(info_file)
    )

    assert (
        original_path
        == "/home/user/Descargas/example.txt"
    )

    assert deletion_date is not None
    assert deletion_date.year == 2026
    assert deletion_date.month == 10
    assert deletion_date.day == 8


def test_scan_trash_reads_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trash_directory = tmp_path / "Trash"

    files_directory = (
        trash_directory / "files"
    )

    info_directory = (
        trash_directory / "info"
    )

    create_file(
        files_directory / "document.txt",
        1024,
    )

    info_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    info_file = (
        info_directory
        / "document.txt.trashinfo"
    )

    info_file.write_text(
        "[Trash Info]\n"
        "Path=/home/user/document.txt\n"
        "DeletionDate=2026-10-08T10:00:00\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        trash,
        "get_trash_directory",
        lambda: trash_directory,
    )

    entries = trash.scan_trash()

    assert len(entries) == 1

    entry = entries[0]

    assert (
        entry.original_path
        == "/home/user/document.txt"
    )

    assert entry.deletion_date is not None
