from pathlib import Path

import linsweep.modules.pacman as pacman
from linsweep.models import CachedPackage, PackageStatus


def make_package(
    name: str,
    version: str,
) -> CachedPackage:
    return CachedPackage(
        name=name,
        version=version,
        architecture="x86_64",
        path=Path(f"/tmp/{name}-{version}-x86_64.pkg.tar.zst"),
        size_bytes=1024,
    )


def fake_compare_versions(
    version_a: str,
    version_b: str,
) -> int:
    a = int(version_a.split("-", 1)[0])
    b = int(version_b.split("-", 1)[0])

    if a > b:
        return 1

    if a < b:
        return -1

    return 0


def test_parse_package_filename(
    tmp_path: Path,
) -> None:
    package_file = (
        tmp_path
        / "example-package-3.2.1-4-x86_64.pkg.tar.zst"
    )

    package_file.write_bytes(b"test")

    package = pacman.parse_package_filename(
        package_file
    )

    assert package is not None
    assert package.name == "example-package"
    assert package.version == "3.2.1-4"
    assert package.architecture == "x86_64"
    assert package.size_bytes == 4


def test_parse_invalid_filename(
    tmp_path: Path,
) -> None:
    file = tmp_path / "archivo.txt"
    file.write_text("test")

    package = pacman.parse_package_filename(file)

    assert package is None


def test_classify_installed_backup_and_old(
    monkeypatch,
) -> None:
    packages = [
        make_package("example", "3-1"),
        make_package("example", "2-1"),
        make_package("example", "1-1"),
    ]

    monkeypatch.setattr(
        pacman,
        "get_installed_packages",
        lambda: {
            "example": "3-1",
        },
    )

    monkeypatch.setattr(
        pacman,
        "compare_versions",
        fake_compare_versions,
    )

    pacman.classify_packages(packages)

    statuses = {
        package.version: package.status
        for package in packages
    }

    assert statuses["3-1"] == PackageStatus.INSTALLED
    assert statuses["2-1"] == PackageStatus.BACKUP
    assert statuses["1-1"] == PackageStatus.OLD


def test_classify_newer_package(
    monkeypatch,
) -> None:
    packages = [
        make_package("example", "4-1"),
        make_package("example", "3-1"),
        make_package("example", "2-1"),
    ]

    monkeypatch.setattr(
        pacman,
        "get_installed_packages",
        lambda: {
            "example": "3-1",
        },
    )

    monkeypatch.setattr(
        pacman,
        "compare_versions",
        fake_compare_versions,
    )

    pacman.classify_packages(packages)

    statuses = {
        package.version: package.status
        for package in packages
    }

    assert statuses["4-1"] == PackageStatus.NEWER
    assert statuses["3-1"] == PackageStatus.INSTALLED
    assert statuses["2-1"] == PackageStatus.BACKUP


def test_classify_not_installed(
    monkeypatch,
) -> None:
    packages = [
        make_package("removed-package", "2-1"),
        make_package("removed-package", "1-1"),
    ]

    monkeypatch.setattr(
        pacman,
        "get_installed_packages",
        lambda: {},
    )

    monkeypatch.setattr(
        pacman,
        "compare_versions",
        fake_compare_versions,
    )

    pacman.classify_packages(packages)

    for package in packages:
        assert (
            package.status
            == PackageStatus.NOT_INSTALLED
        )


def test_scan_pacman_cache_ignores_signatures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_file = (
        tmp_path
        / "example-1.0-1-x86_64.pkg.tar.zst"
    )

    signature_file = (
        tmp_path
        / "example-1.0-1-x86_64.pkg.tar.zst.sig"
    )

    package_file.write_bytes(b"package")
    signature_file.write_bytes(b"signature")

    monkeypatch.setattr(
        pacman,
        "PACMAN_CACHE",
        tmp_path,
    )

    packages = pacman.scan_pacman_cache()

    assert len(packages) == 1
    assert packages[0].name == "example"
