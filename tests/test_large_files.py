import sys
from pathlib import Path

import linsweep.main as main_module
from linsweep.modules.large_files import scan_large_files


def create_file(
    path: Path,
    size: int,
) -> None:
    path.write_bytes(b"\0" * size)


def test_finds_files_larger_than_minimum(
    tmp_path: Path,
) -> None:
    small_file = tmp_path / "small.bin"
    large_file = tmp_path / "large.bin"

    create_file(small_file, 512)
    create_file(large_file, 2048)

    results = scan_large_files(
        root=tmp_path,
        min_size=1024,
    )

    paths = {
        item.path
        for item in results
    }

    assert large_file in paths
    assert small_file not in paths


def test_scan_does_not_leave_root_directory(
    tmp_path: Path,
) -> None:
    scan_directory = tmp_path / "scan"
    outside_directory = tmp_path / "outside"

    scan_directory.mkdir()
    outside_directory.mkdir()

    inside_file = scan_directory / "inside.bin"
    outside_file = outside_directory / "outside.bin"

    create_file(inside_file, 2048)
    create_file(outside_file, 4096)

    results = scan_large_files(
        root=scan_directory,
        min_size=1024,
    )

    paths = {
        item.path
        for item in results
    }

    assert inside_file in paths
    assert outside_file not in paths


def test_cli_large_files_respects_path(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    scan_directory = tmp_path / "scan"
    outside_directory = tmp_path / "outside"

    scan_directory.mkdir()
    outside_directory.mkdir()

    inside_file = scan_directory / "inside.bin"
    outside_file = outside_directory / "outside.bin"

    create_file(inside_file, 2048)
    create_file(outside_file, 4096)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "linsweep",
            "large-files",
            "--path",
            str(scan_directory),
            "--min-size",
            "1K",
        ],
    )

    main_module.main()

    output = capsys.readouterr().out

    assert "inside.bin" in output
    assert "outside.bin" not in output
    assert str(scan_directory) in output

