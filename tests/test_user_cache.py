from pathlib import Path

import linsweep.modules.user_cache as user_cache
from linsweep.models import RiskLevel


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


def test_classify_safe_cache() -> None:
    risk, description = user_cache.classify_cache(
        "mozilla"
    )

    assert risk == RiskLevel.SAFE
    assert description


def test_classify_review_cache() -> None:
    risk, description = user_cache.classify_cache(
        "JetBrains"
    )

    assert risk == RiskLevel.REVIEW
    assert description


def test_classify_unknown_cache() -> None:
    risk, description = user_cache.classify_cache(
        "some-unknown-application"
    )

    assert risk == RiskLevel.UNKNOWN
    assert description


def test_scan_user_cache_excludes_managed_cache(
    tmp_path: Path,
    monkeypatch,
) -> None:
    yay_directory = tmp_path / "yay"
    mozilla_directory = tmp_path / "mozilla"

    yay_directory.mkdir()
    mozilla_directory.mkdir()

    create_file(
        yay_directory / "package.bin",
        4096,
    )

    create_file(
        mozilla_directory / "cache.bin",
        2048,
    )

    monkeypatch.setattr(
        user_cache,
        "USER_CACHE",
        tmp_path,
    )

    entries = user_cache.scan_user_cache()

    names = {
        entry.name
        for entry in entries
    }

    assert "mozilla" in names
    assert "yay" not in names


def test_scan_user_cache_calculates_size(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_directory = tmp_path / "mozilla"

    create_file(
        cache_directory / "first.bin",
        1024,
    )

    create_file(
        cache_directory / "nested" / "second.bin",
        2048,
    )

    monkeypatch.setattr(
        user_cache,
        "USER_CACHE",
        tmp_path,
    )

    entries = user_cache.scan_user_cache()

    assert len(entries) == 1

    entry = entries[0]

    assert entry.name == "mozilla"
    assert entry.size_bytes == 3072
    assert entry.risk == RiskLevel.SAFE
