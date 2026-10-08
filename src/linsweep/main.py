import argparse
import shutil

from linsweep.models import PackageStatus
from linsweep.modules.pacman import (
    classify_packages,
    scan_pacman_cache,
)

from linsweep.modules.journal import (
    calculate_recoverable,
    get_journal_disk_usage,
)

from linsweep.modules.yay import scan_yay_cache

from linsweep.modules.user_cache import scan_user_cache

def format_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]

    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} EiB"


def show_disk_usage() -> None:
    total, used, free = shutil.disk_usage("/")

    percent = (used / total) * 100 if total else 0

    print("=== SISTEMA ===")
    print(f"Total:   {format_size(total)}")
    print(f"Usado:   {format_size(used)} ({percent:.1f}%)")
    print(f"Libre:   {format_size(free)}")
    print()

def show_journal() -> None:
    print("=== SYSTEMD JOURNAL ===")

    usage = get_journal_disk_usage()

    if usage is None:
        print(
            "No fue posible determinar "
            "el tamaño del journal."
        )
        print()
        return

    print(
        f"Espacio utilizado: "
        f"{format_size(usage)}"
    )

    print()
    print("Posibles límites:")
    print()

    targets = [
        100 * 1024 ** 2,
        250 * 1024 ** 2,
        500 * 1024 ** 2,
        1024 ** 3,
    ]

    for target in targets:
        recoverable = calculate_recoverable(
            usage,
            target,
        )

        print(
            f"  Máximo {format_size(target):>10}"
            f"  → recuperable: "
            f"{format_size(recoverable)}"
        )

    print()

def get_packages():
    return classify_packages(
        scan_pacman_cache()
    )


def count_status(packages, status: PackageStatus) -> int:
    return sum(
        1
        for package in packages
        if package.status == status
    )


def size_status(packages, status: PackageStatus) -> int:
    return sum(
        package.size_bytes
        for package in packages
        if package.status == status
    )


def show_pacman_cache(details: bool = False) -> None:
    print("=== PACMAN CACHE ===")

    packages = get_packages()

    if not packages:
        print("No se encontraron paquetes.")
        print()
        return

    total_size = sum(
        package.size_bytes
        for package in packages
    )

    installed_count = count_status(
        packages,
        PackageStatus.INSTALLED,
    )

    backup_count = count_status(
        packages,
        PackageStatus.BACKUP,
    )

    newer_count = count_status(
        packages,
        PackageStatus.NEWER,
    )

    old_count = count_status(
        packages,
        PackageStatus.OLD,
    )

    not_installed_count = count_status(
        packages,
        PackageStatus.NOT_INSTALLED,
    )

    installed_size = size_status(
        packages,
        PackageStatus.INSTALLED,
    )

    backup_size = size_status(
        packages,
        PackageStatus.BACKUP,
    )

    newer_size = size_status(
        packages,
        PackageStatus.NEWER,
    )

    old_size = size_status(
        packages,
        PackageStatus.OLD,
    )

    not_installed_size = size_status(
        packages,
        PackageStatus.NOT_INSTALLED,
    )

    recoverable_count = (
        old_count
        + not_installed_count
    )

    recoverable_size = (
        old_size
        + not_installed_size
    )

    print(
        f"Paquetes almacenados:       "
        f"{len(packages):4} archivos   "
        f"{format_size(total_size)}"
    )

    print()

    print(
        f"Versiones instaladas:       "
        f"{installed_count:4} archivos   "
        f"{format_size(installed_size)}"
    )

    print(
        f"Versiones de respaldo:      "
        f"{backup_count:4} archivos   "
        f"{format_size(backup_size)}"
    )

    print(
        f"Versiones más nuevas:       "
        f"{newer_count:4} archivos   "
        f"{format_size(newer_size)}"
    )

    print(
        f"Versiones antiguas:         "
        f"{old_count:4} archivos   "
        f"{format_size(old_size)}"
    )

    print(
        f"Paquetes no instalados:     "
        f"{not_installed_count:4} archivos   "
        f"{format_size(not_installed_size)}"
    )

    print()

    print("Potencialmente recuperable:")
    print(f"  Archivos: {recoverable_count}")
    print(f"  Espacio:  {format_size(recoverable_size)}")
    print()

    if details:
        show_package_details(packages)

def show_yay_cache(details: bool = False) -> None:
    print("=== YAY / AUR CACHE ===")

    entries = scan_yay_cache()

    if not entries:
        print("No se encontró caché de Yay.")
        print()
        return

    total_size = sum(
        entry.total_size
        for entry in entries
    )

    current_size = sum(
        entry.compiled_current_size
        for entry in entries
    )

    old_size = sum(
        entry.compiled_old_size
        for entry in entries
    )

    newer_size = sum(
        entry.compiled_newer_size
        for entry in entries
    )

    not_installed_size = sum(
        entry.compiled_not_installed_size
        for entry in entries
    )

    sources_size = sum(
        entry.downloaded_sources_size
        for entry in entries
    )

    git_size = sum(
        entry.git_size
        for entry in entries
    )

    metadata_size = sum(
        entry.metadata_size
        for entry in entries
    )

    other_size = sum(
        entry.other_size
        for entry in entries
    )

    safe_recoverable = (
        sources_size + old_size
    )

    review_recoverable = (
        not_installed_size
    )

    print(f"Paquetes/directorios:       {len(entries)}")
    print(f"Espacio utilizado:          {format_size(total_size)}")
    print()

    print(
        f"Compilados actuales:        "
        f"{format_size(current_size)}"
    )

    print(
        f"Compilados antiguos:        "
        f"{format_size(old_size)}"
    )

    print(
        f"Compilados más nuevos:      "
        f"{format_size(newer_size)}"
    )

    print(
        f"Compilados no instalados:   "
        f"{format_size(not_installed_size)}"
    )

    print(
        f"Fuentes descargadas:        "
        f"{format_size(sources_size)}"
    )

    print(
        f"Repositorios Git:           "
        f"{format_size(git_size)}"
    )

    print(
        f"Metadatos AUR:              "
        f"{format_size(metadata_size)}"
    )

    print(
        f"Otros archivos:             "
        f"{format_size(other_size)}"
    )

    print("Potencialmente recuperable:")
    print(
        f"  Seguro:    "
        f"{format_size(safe_recoverable)}"
    )

    print(
        f"  A revisar: "
        f"{format_size(review_recoverable)}"
    )

    print()

    if details:
        entries.sort(
            key=lambda entry: entry.total_size,
            reverse=True,
        )

        for entry in entries:

            print(
                f"{entry.name} "
                f"({format_size(entry.total_size)})"
            )

            print(
                f"  compilado actual:      "
                f"{format_size(entry.compiled_current_size)}"
            )

            print(
                f"  compilados antiguos:   "
                f"{format_size(entry.compiled_old_size)}"
            )

            print(
                f"  compilados nuevos:     "
                f"{format_size(entry.compiled_newer_size)}"
            )

            print(
                f"  no instalados:         "
                f"{format_size(entry.compiled_not_installed_size)}"
            )

            print(
                f"  fuentes descargadas:   "
                f"{format_size(entry.downloaded_sources_size)}"
            )

            print(
                f"  git:                   "
                f"{format_size(entry.git_size)}"
            )

            print(
                f"  metadatos:             "
                f"{format_size(entry.metadata_size)}"
            )

            print(
                f"  otros:                 "
                f"{format_size(entry.other_size)}"
            )

            print()


def show_user_cache(details: bool = False) -> None:
    print("=== CACHÉ DE USUARIO ===")

    entries = scan_user_cache()

    if not entries:
        print("No se encontró caché de usuario.")
        print()
        return

    total_size = sum(
        entry.size_bytes
        for entry in entries
    )

    entries.sort(
        key=lambda entry: entry.size_bytes,
        reverse=True,
    )

    print(f"Directorios encontrados:    {len(entries)}")
    print(f"Espacio utilizado:          {format_size(total_size)}")
    print()

    print("Directorios más grandes:")

    limit = len(entries) if details else 10

    for entry in entries[:limit]:
        print(
            f"{format_size(entry.size_bytes):>10}  "
            f"{entry.name}"
        )

    print()

    if not details and len(entries) > 10:
        print(
            f"Mostrando 10 de {len(entries)} directorios."
        )
        print(
            "Usa 'linsweep cache --details' "
            "para ver todos."
        )
        print()

def show_package_details(packages) -> None:

    old_packages = [
        package
        for package in packages
        if package.status == PackageStatus.OLD
    ]

    not_installed_packages = [
        package
        for package in packages
        if package.status == PackageStatus.NOT_INSTALLED
    ]

    old_packages.sort(
        key=lambda package: package.size_bytes,
        reverse=True,
    )

    not_installed_packages.sort(
        key=lambda package: package.size_bytes,
        reverse=True,
    )

    print("=== VERSIONES ANTIGUAS ===")

    if not old_packages:
        print("Ninguna.")
    else:
        for package in old_packages:
            print(
                f"{format_size(package.size_bytes):>10}  "
                f"{package.name} "
                f"{package.version}"
            )

    print()

    print("=== PAQUETES NO INSTALADOS ===")

    if not not_installed_packages:
        print("Ninguno.")
    else:
        for package in not_installed_packages:
            print(
                f"{format_size(package.size_bytes):>10}  "
                f"{package.name} "
                f"{package.version}"
            )

    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linsweep",
        description=(
            "Herramienta de análisis y mantenimiento "
            "seguro para Linux."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    packages_parser = subparsers.add_parser(
        "packages",
        help="Analiza la caché de paquetes de Pacman.",
    )

    packages_parser.add_argument(
        "--details",
        action="store_true",
        help=(
            "Muestra los paquetes antiguos y "
            "los paquetes no instalados."
        ),
    )

    subparsers.add_parser(
        "journal",
        help="Analiza el espacio utilizado por systemd journal.",
    )

    yay_parser = subparsers.add_parser(
        "yay",
    	help="Analiza la caché de Yay/AUR.",
    )

    yay_parser.add_argument(
        "--details",
    	action="store_true",
        help="Muestra el tamaño de cada directorio de Yay.",
    )

    cache_parser = subparsers.add_parser(
        "cache",
        help="Analiza la caché del usuario.",
    )

    cache_parser.add_argument(
        "--details",
    	action="store_true",
    	help="Muestra todos los directorios de caché.",
    )

    return parser


def main() -> None:
    parser = build_parser()

    args = parser.parse_args()

    print()
    print("LinSweep")
    print("========")
    print()

    if args.command == "packages":
        show_pacman_cache(
            details=args.details
        )
        return
    if args.command == "journal":
        show_journal()
        return
    
    if args.command == "yay":
        show_yay_cache(
            details=args.details
        )
        return
    if args.command == "cache":
        show_user_cache(
            details=args.details
        )
        return

    show_disk_usage()
    show_pacman_cache()
    show_journal()
    show_yay_cache()    

if __name__ == "__main__":
    main()
