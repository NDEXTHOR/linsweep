import os
import re
import subprocess


def parse_size(size_text: str) -> int | None:
    """
    Convierte valores como:

    512M
    1.4G
    800K

    a bytes.
    """

    match = re.fullmatch(
        r"([\d.]+)\s*([KMGTPE]?)(?:i?B|B)?",
        size_text.strip(),
        re.IGNORECASE,
    )

    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2).upper()

    powers = {
        "": 0,
        "K": 1,
        "M": 2,
        "G": 3,
        "T": 4,
        "P": 5,
        "E": 6,
    }

    return int(value * (1024 ** powers[unit]))


def get_journal_disk_usage() -> int | None:
    """
    Obtiene el espacio ocupado por los journals
    activos y archivados utilizando journalctl.
    """

    env = os.environ.copy()
    env["LC_ALL"] = "C"

    try:
        result = subprocess.run(
            [
                "journalctl",
                "--disk-usage",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        return None

    # Ejemplo:
    #
    # Archived and active journals take up 1.2G
    # in the file system.

    match = re.search(
        r"take up\s+([\d.]+\s*[KMGTPE]?(?:i?B|B)?)",
        result.stdout,
        re.IGNORECASE,
    )

    if not match:
        return None

    return parse_size(match.group(1))


def calculate_recoverable(
    current_size: int,
    target_size: int,
) -> int:
    """
    Calcula cuánto podría reducirse el journal
    si se estableciera un tamaño máximo.
    """

    return max(
        0,
        current_size - target_size,
    )

