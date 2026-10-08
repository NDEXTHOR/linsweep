from pathlib import Path

import linsweep.modules.yay as yay


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


def test_scan_yay_cache_classifies_current_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir
        / "example-2-1-x86_64.pkg.tar.zst",
        2048,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {
            "example": "2-1",
        },
    )

    monkeypatch.setattr(
        yay,
        "compare_versions",
        lambda a, b: (
            0 if a == b
            else 1 if a > b
            else -1
        ),
    )

    entries = yay.scan_yay_cache()

    assert len(entries) == 1

    entry = entries[0]

    assert entry.compiled_current_size == 2048
    assert entry.compiled_current_count == 1


def test_scan_yay_cache_classifies_old_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir
        / "example-1-1-x86_64.pkg.tar.zst",
        2048,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {
            "example": "2-1",
        },
    )

    monkeypatch.setattr(
        yay,
        "compare_versions",
        lambda a, b: (
            0 if a == b
            else 1 if a > b
            else -1
        ),
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert entry.compiled_old_size == 2048
    assert entry.compiled_old_count == 1


def test_scan_yay_cache_classifies_newer_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir
        / "example-3-1-x86_64.pkg.tar.zst",
        2048,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {
            "example": "2-1",
        },
    )

    monkeypatch.setattr(
        yay,
        "compare_versions",
        lambda a, b: (
            0 if a == b
            else 1 if a > b
            else -1
        ),
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert entry.compiled_newer_size == 2048
    assert entry.compiled_newer_count == 1


def test_scan_yay_cache_classifies_not_installed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir
        / "example-1-1-x86_64.pkg.tar.zst",
        2048,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {},
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert (
        entry.compiled_not_installed_size
        == 2048
    )

    assert (
        entry.compiled_not_installed_count
        == 1
    )


def test_scan_yay_cache_classifies_downloaded_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir / "source.deb",
        4096,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {},
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert entry.downloaded_sources_size == 4096


def test_scan_yay_cache_classifies_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir / "PKGBUILD",
        100,
    )

    create_file(
        package_dir / ".SRCINFO",
        200,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {},
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert entry.metadata_size == 300


def test_scan_yay_cache_classifies_git_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir / ".git" / "objects" / "test",
        1024,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {},
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert entry.git_size == 1024


def test_scan_yay_cache_classifies_other_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "example"
    package_dir.mkdir()

    create_file(
        package_dir / "unknown.data",
        512,
    )

    monkeypatch.setattr(
        yay,
        "YAY_CACHE",
        tmp_path,
    )

    monkeypatch.setattr(
        yay,
        "get_installed_packages",
        lambda: {},
    )

    entries = yay.scan_yay_cache()

    entry = entries[0]

    assert entry.other_size == 512
