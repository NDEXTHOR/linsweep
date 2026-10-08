import linsweep.modules.journal as journal


def test_parse_size_bytes() -> None:
    assert journal.parse_size("512 B") == 512


def test_parse_size_megabytes() -> None:
    assert journal.parse_size("100M") == 100 * 1024 ** 2


def test_parse_size_gigabytes() -> None:
    assert journal.parse_size("1.5G") == int(
        1.5 * 1024 ** 3
    )


def test_parse_invalid_size() -> None:
    assert journal.parse_size("desconocido") is None


def test_calculate_recoverable() -> None:
    current = 500 * 1024 ** 2
    target = 100 * 1024 ** 2

    assert journal.calculate_recoverable(
        current,
        target,
    ) == 400 * 1024 ** 2


def test_calculate_recoverable_never_negative() -> None:
    current = 50 * 1024 ** 2
    target = 100 * 1024 ** 2

    assert journal.calculate_recoverable(
        current,
        target,
    ) == 0
