import pytest

from linsweep.main import parse_size


def test_parse_size_megabytes() -> None:
    assert parse_size("100M") == 100 * 1024 ** 2


def test_parse_size_gigabytes() -> None:
    assert parse_size("1G") == 1024 ** 3


def test_parse_size_decimal_gigabytes() -> None:
    assert parse_size("2.5G") == int(
        2.5 * 1024 ** 3
    )


def test_parse_size_case_insensitive() -> None:
    assert parse_size("500m") == 500 * 1024 ** 2


def test_parse_size_invalid() -> None:
    with pytest.raises(Exception):
        parse_size("abc")
