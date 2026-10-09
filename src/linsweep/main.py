import argparse
import shutil

from linsweep.models import PackageStatus, RiskLevel
from linsweep.modules.yay import scan_yay_cache
from linsweep.modules.user_cache import scan_user_cache
from linsweep.modules.large_files import scan_large_files
from linsweep.modules.temp_files import scan_temp_files
from pathlib import Path

from linsweep.modules.pacman import (
    classify_packages,
    scan_pacman_cache,
    get_orphan_packages,
)
from linsweep.modules.journal import (
    calculate_recoverable,
    get_journal_disk_usage,
)
from linsweep.modules.trash import (
    get_trash_directory,
    scan_trash,
)
from linsweep.modules.cleanup import (
    execute_pacman_cleanup,
    execute_trash_cleanup,
    execute_yay_cleanup,
    get_pacman_cleanup_candidates,
    get_trash_cleanup_candidates,
    get_yay_cleanup_candidates,
)

def format_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]

    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} EiB"

def parse_size(value: str) -> int:
    value = value.strip().upper()

    units = {
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "KIB": 1024,
        "M": 1024 ** 2,
        "MB": 1024 ** 2,
        "MIB": 1024 ** 2,
        "G": 1024 ** 3,
        "GB": 1024 ** 3,
        "GIB": 1024 ** 3,
        "T": 1024 ** 4,
        "TB": 1024 ** 4,
        "TIB": 1024 ** 4,
    }

    for unit in sorted(
        units,
        key=len,
        reverse=True,
    ):
        if value.endswith(unit):
            number = value[:-len(unit)]

            try:
                return int(
                    float(number) * units[unit]
                )
            except ValueError:
                break

    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Tamaño inválido: {value}. "
            "Ejemplos: 500M, 1G, 2.5G"
        )

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

    show_orphan_packages(
        details=details
    )

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

    entries.sort(
        key=lambda entry: entry.size_bytes,
        reverse=True,
    )

    total_size = sum(
        entry.size_bytes
        for entry in entries
    )

    safe_entries = [
        entry
        for entry in entries
        if entry.risk == RiskLevel.SAFE
    ]

    review_entries = [
        entry
        for entry in entries
        if entry.risk == RiskLevel.REVIEW
    ]

    unknown_entries = [
        entry
        for entry in entries
        if entry.risk == RiskLevel.UNKNOWN
    ]

    dangerous_entries = [
        entry
        for entry in entries
        if entry.risk == RiskLevel.DANGEROUS
    ]

    safe_size = sum(
        entry.size_bytes
        for entry in safe_entries
    )

    review_size = sum(
        entry.size_bytes
        for entry in review_entries
    )

    unknown_size = sum(
        entry.size_bytes
        for entry in unknown_entries
    )

    dangerous_size = sum(
        entry.size_bytes
        for entry in dangerous_entries
    )

    print(
        f"Directorios encontrados:    {len(entries)}"
    )

    print(
        f"Espacio utilizado:          {format_size(total_size)}"
    )

    print()

    print(
        f"Seguro / reconstruible:     "
        f"{len(safe_entries):3} directorios   "
        f"{format_size(safe_size)}"
    )

    print(
        f"Requiere revisión:          "
        f"{len(review_entries):3} directorios   "
        f"{format_size(review_size)}"
    )

    print(
        f"Desconocido:                "
        f"{len(unknown_entries):3} directorios   "
        f"{format_size(unknown_size)}"
    )

    if dangerous_entries:
        print(
            f"Peligroso:                  "
            f"{len(dangerous_entries):3} directorios   "
            f"{format_size(dangerous_size)}"
        )

    print()

    print("Potencialmente recuperable:")
    print(
        f"  Bajo riesgo: {format_size(safe_size)}"
    )

    print()

    print("Directorios más grandes:")

    labels = {
        RiskLevel.SAFE: "SAFE",
        RiskLevel.REVIEW: "REVIEW",
        RiskLevel.UNKNOWN: "UNKNOWN",
        RiskLevel.DANGEROUS: "DANGER",
    }

    limit = len(entries) if details else 10

    for entry in entries[:limit]:
        label = labels[entry.risk]

        print(
            f"{format_size(entry.size_bytes):>10}  "
            f"{label:<7}  "
            f"{entry.name}"
        )

        if details:
            print(
                f"{'':12}{entry.description}"
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

def show_large_files(root: Path,min_size: int,) -> None:
    print("=== ARCHIVOS GRANDES ===")

    files = scan_large_files(
	root=root,
        min_size=min_size,
    )

    print(
        f"Ruta analizada: {root}"
    )

    print(
        f"Tamaño mínimo: {format_size(min_size)}"
    )

    print()

    if not files:
        print(
            "No se encontraron archivos "
            "que superen el tamaño mínimo."
        )
        print()
        return

    print(
        f"Archivos encontrados: {len(files)}"
    )

    print()

    for file in files:
        try:
            display_path = (
                "~/" + str(
                    file.path.relative_to(
                        Path.home()
                    )
                )
            )
        except ValueError:
            display_path = str(file.path)

        print(
            f"{format_size(file.size_bytes):>10}  "
            f"{display_path}"
        )

    print()

def show_orphan_packages(details: bool = False,) -> None:
    print("=== PAQUETES HUÉRFANOS ===")

    orphans = get_orphan_packages()

    if not orphans:
        print("No se encontraron paquetes huérfanos.")
        print()
        return

    total_size = sum(
        package.size_bytes
        for package in orphans
    )

    print(
        f"Paquetes encontrados:       {len(orphans)}"
    )
    print(
        f"Tamaño instalado:           "
        f"{format_size(total_size)}"
    )
    print("Clasificación:              REVIEW")
    print()

    print(
        "Estos paquetes fueron instalados como "
        "dependencias y actualmente no son requeridos."
    )
    print(
        "No se consideran automáticamente seguros "
        "para eliminar."
    )
    print()

    if details:
        for package in orphans:
            print(
                f"{format_size(package.size_bytes):>10}  "
                f"{package.name} {package.version}"
            )

        print()

def show_trash(details: bool = False,) -> None:
    print("=== PAPELERA ===")

    entries = scan_trash()

    total_size = sum(
        entry.size_bytes
        for entry in entries
    )

    print(
        f"Ruta:                       "
        f"{get_trash_directory()}"
    )

    print(
        f"Elementos encontrados:       "
        f"{len(entries)}"
    )

    print(
        f"Espacio utilizado:           "
        f"{format_size(total_size)}"
    )

    print()

    if not entries:
        print("La papelera está vacía.")
        print()
        return

    dates = [
        entry.deletion_date
        for entry in entries
        if entry.deletion_date is not None
    ]

    if dates:
        oldest = min(dates)

        print(
            f"Elemento más antiguo:        "
            f"{oldest:%Y-%m-%d %H:%M:%S}"
        )

    print()
    print("Potencialmente recuperable:")
    print(
        f"  Espacio: {format_size(total_size)}"
    )
    print("  Clasificación: REVIEW")
    print()

    if details:
        for entry in entries:
            print(
                f"{format_size(entry.size_bytes):>10}  "
                f"{entry.name}"
            )

            if entry.original_path:
                print(
                    f"            Origen: "
                    f"{entry.original_path}"
                )

            if entry.deletion_date:
                print(
                    f"            Eliminado: "
                    f"{entry.deletion_date:%Y-%m-%d %H:%M:%S}"
                )

            print()

def show_temp_files(details: bool = False,) -> None:
    print("=== ARCHIVOS TEMPORALES ===")

    files = scan_temp_files()

    tmp_files = [
        file
        for file in files
        if file.path.is_relative_to("/tmp")
    ]

    var_tmp_files = [
        file
        for file in files
        if file.path.is_relative_to("/var/tmp")
    ]

    recent = [
        file
        for file in files
        if file.age_days < 1
    ]

    medium = [
        file
        for file in files
        if 1 <= file.age_days <= 7
    ]

    old = [
        file
        for file in files
        if file.age_days > 7
    ]

    def total_size(items) -> int:
        return sum(
            item.size_bytes
            for item in items
        )

    print("/tmp")
    print(
        f"  Archivos propios:         "
        f"{len(tmp_files)}"
    )
    print(
        f"  Espacio utilizado:        "
        f"{format_size(total_size(tmp_files))}"
    )

    print()

    print("/var/tmp")
    print(
        f"  Archivos propios:         "
        f"{len(var_tmp_files)}"
    )
    print(
        f"  Espacio utilizado:        "
        f"{format_size(total_size(var_tmp_files))}"
    )

    print()
    print("Antigüedad:")

    print(
        f"  < 1 día:                  "
        f"{format_size(total_size(recent))}"
    )

    print(
        f"  1 - 7 días:               "
        f"{format_size(total_size(medium))}"
    )

    print(
        f"  > 7 días:                 "
        f"{format_size(total_size(old))}"
    )

    print()
    print("Potencialmente revisable:")

    print(
        f"  Archivos > 7 días:        "
        f"{len(old)}"
    )

    print(
        f"  Espacio:                  "
        f"{format_size(total_size(old))}"
    )

    print(
        "  Clasificación:            REVIEW"
    )

    print()

    if details:
        print("Archivos a revisar (> 7 días):")
        print()

        if not old:
            print("No se encontraron archivos antiguos.")
            print()
            return

        old_sorted = sorted(
            old,
            key=lambda item: (
                item.age_days,
                item.size_bytes,
            ),
            reverse=True,
        )

        for file in old_sorted:
            print(
                f"{format_size(file.size_bytes):>10}  "
                f"{file.age_days:6.1f} días  "
                f"{file.path}"
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

def clean_pacman_cache(dry_run: bool = False,) -> None:
    print("=== LIMPIEZA DE CACHÉ PACMAN ===")
    print()

    candidates = (
        get_pacman_cleanup_candidates()
    )

    if not candidates:
        print(
            "No se encontraron archivos "
            "de caché para limpiar."
        )
        print()
        return

    old_packages = [
        package
        for package in candidates
        if package.status == PackageStatus.OLD
    ]

    uninstalled_packages = [
        package
        for package in candidates
        if package.status
        == PackageStatus.NOT_INSTALLED
    ]

    total_size = sum(
        package.size_bytes
        for package in candidates
    )

    print(
        f"Versiones antiguas:         "
        f"{len(old_packages)}"
    )

    print(
        f"Paquetes no instalados:     "
        f"{len(uninstalled_packages)}"
    )

    print(
        f"Total de archivos:          "
        f"{len(candidates)}"
    )

    print(
        f"Espacio recuperable:        "
        f"{format_size(total_size)}"
    )

    print()
    print("Archivos que se eliminarían:")
    print()

    for package in candidates:
        if package.status == PackageStatus.OLD:
            status = "OLD"
        else:
            status = "NOT_INSTALLED"

        print(
            f"{format_size(package.size_bytes):>10}  "
            f"{status:<13}  "
            f"{package.path}"
        )

    print()

    if dry_run:
        print(
            "DRY-RUN: no se realizó "
            "ningún cambio."
        )
        print()
        return

    print(
        "LinSweep eliminará únicamente "
        "los archivos mostrados por la política "
        "de limpieza de Pacman."
    )

    print(
        "Se conservará la versión instalada "
        "y una versión de respaldo."
    )

    print()

    try:
        confirmation = input(
            'Escribe "ELIMINAR" para continuar: '
        )
    except (
        KeyboardInterrupt,
        EOFError,
    ):
        print()
        print("Limpieza cancelada.")
        return

    if confirmation != "ELIMINAR":
        print()
        print("Limpieza cancelada.")
        return

    print()

    success, message = (
        execute_pacman_cleanup()
    )

    print(message)

    if success:
        print(
            f"Espacio recuperable estimado: "
            f"{format_size(total_size)}"
        )

    print()

def clean_trash(dry_run: bool = False,) -> None:
    print("=== LIMPIEZA DE PAPELERA ===")
    print()

    entries = get_trash_cleanup_candidates()

    if not entries:
        print("La papelera está vacía.")
        print()
        return

    total_size = sum(
        entry.size_bytes
        for entry in entries
    )

    print(
        f"Elementos encontrados:      "
        f"{len(entries)}"
    )

    print(
        f"Espacio recuperable:        "
        f"{format_size(total_size)}"
    )

    print()
    print("Elementos que se eliminarían:")
    print()

    for entry in entries:
        print(
            f"{format_size(entry.size_bytes):>10}  "
            f"{entry.name}"
        )

        if entry.original_path:
            print(
                f"            Origen: "
                f"{entry.original_path}"
            )

        if entry.deletion_date:
            print(
                f"            Eliminado: "
                f"{entry.deletion_date:%Y-%m-%d %H:%M:%S}"
            )

        print()

    if dry_run:
        print(
            "DRY-RUN: no se realizó "
            "ningún cambio."
        )
        print()
        return

    print(
        "ADVERTENCIA: los elementos mostrados "
        "serán eliminados permanentemente."
    )

    print(
        "LinSweep no podrá restaurarlos después."
    )

    print()

    try:
        confirmation = input(
            'Escribe "VACIAR" para continuar: '
        )

    except (
        KeyboardInterrupt,
        EOFError,
    ):
        print()
        print("Limpieza cancelada.")
        return

    if confirmation != "VACIAR":
        print()
        print("Limpieza cancelada.")
        return

    print()

    success, deleted_count, message = (
        execute_trash_cleanup(entries)
    )

    print(message)

    print(
        f"Elementos eliminados:       "
        f"{deleted_count}"
    )

    remaining = (
        get_trash_cleanup_candidates()
    )

    remaining_size = sum(
        entry.size_bytes
        for entry in remaining
    )

    recovered = max(
        0,
        total_size - remaining_size,
    )

    print(
        f"Espacio recuperado estimado: "
        f"{format_size(recovered)}"
    )

    if not success:
        print(
            "La limpieza no terminó completamente. "
            "Ejecuta 'linsweep trash' para revisar "
            "el estado actual."
        )

    print()

def clean_yay(dry_run: bool = False) -> None:
    print("=== LIMPIEZA DE CACHÉ YAY ===")
    print()

    candidates = get_yay_cleanup_candidates()

    if not candidates:
        print("No se encontraron fuentes descargadas para limpiar.")
        print()
        return

    total_size = sum(
        candidate.size_bytes
        for candidate in candidates
    )

    file_word = (
        "archivo"
        if len(candidates) == 1
        else "archivos"
    )

    print(
        f"Fuentes descargadas:        "
        f"{len(candidates)} {file_word}"
    )

    print(
        f"Espacio recuperable:        "
        f"{format_size(total_size)}"
    )

    print(
        "Clasificación:              SAFE"
    )

    print()
    print("Archivos que se eliminarían:")
    print()

    for candidate in candidates:
        print(
            f"{format_size(candidate.size_bytes):>10}  "
            f"{candidate.path}"
        )

    print()

    if dry_run:
        print("DRY-RUN: no se realizó ningún cambio.")
        print()
        return

    print(
        "LinSweep eliminará únicamente las fuentes "
        "descargadas mostradas arriba."
    )

    print(
        "No se eliminarán paquetes compilados, "
        "repositorios Git ni metadatos AUR."
    )

    print()

    try:
        confirmation = input(
            'Escribe "ELIMINAR" para continuar: '
        )
    except (KeyboardInterrupt, EOFError):
        print()
        print("Limpieza cancelada.")
        return

    if confirmation != "ELIMINAR":
        print()
        print("Limpieza cancelada.")
        return

    print()

    success, deleted_count, message = execute_yay_cleanup(
        candidates
    )

    print(message)

    print(
        f"Archivos eliminados:        "
        f"{deleted_count}"
    )

    remaining = get_yay_cleanup_candidates()

    remaining_size = sum(
        candidate.size_bytes
        for candidate in remaining
    )

    recovered = max(
        0,
        total_size - remaining_size,
    )

    print(
        f"Espacio recuperado estimado: "
        f"{format_size(recovered)}"
    )

    if not success:
        print(
            "La limpieza no terminó completamente. "
            "Ejecuta 'linsweep yay --details' "
            "para revisar el estado actual."
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

    large_files_parser = subparsers.add_parser(
        "large-files",
    	help="Busca archivos grandes en el directorio del usuario.",
    )

    large_files_parser.add_argument(
        "--min-size",
    	type=parse_size,
    	default=500 * 1024 * 1024,
    	metavar="TAMAÑO",
    	help=(
            "Tamaño mínimo del archivo. "
            "Ejemplos: 100M, 500M, 1G. "
            "Predeterminado: 500M."
        ),
    )

    large_files_parser.add_argument(
        "--path",
    	type=Path,
    	default=Path.home(),
    	metavar="RUTA",
    	help=(
            "Directorio que se analizará. "
        	"Predeterminado: directorio personal."
    	),
    )

    trash_parser = subparsers.add_parser(
        "trash",
    	help="Analiza la papelera del usuario.",
    )

    trash_parser.add_argument(
        "--details",
    	action="store_true",
    	help="Muestra los elementos de la papelera.",
    )

    temp_parser = subparsers.add_parser(
        "temp",
        help="Analiza archivos temporales del usuario.",
    )

    temp_parser.add_argument(
        "--details",
        action="store_true",
        help="Muestra los archivos temporales encontrados.",
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

    clean_parser = subparsers.add_parser(
        "clean",
        help="Ejecuta operaciones de limpieza seguras.",
    )

    clean_subparsers = (
        clean_parser.add_subparsers(
            dest="clean_target",
            required=True,
        )
    )

    clean_packages_parser = (
        clean_subparsers.add_parser(
            "packages",
            help="Limpia la caché antigua de Pacman.",
        )
    )

    clean_packages_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Muestra exactamente qué se eliminaría "
            "sin modificar el sistema."
        ),
    )

    clean_trash_parser = (
        clean_subparsers.add_parser(
            "trash",
            help="Vacía la papelera del usuario.",
        )
    )

    clean_trash_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Muestra exactamente qué se eliminaría "
            "sin modificar la papelera."
        ),
    )

    clean_yay_parser = clean_subparsers.add_parser(
        "yay",
        help="Limpia fuentes descargadas de la caché de Yay.",
    )

    clean_yay_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Muestra exactamente qué se eliminaría "
            "sin modificar la caché de Yay."
        ),
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

    if args.command == "large-files":
        show_large_files(
            root=args.path.expanduser().resolve(),
            min_size=args.min_size,
        )
        return
    
    if args.command == "trash":
        show_trash(
        details=args.details
        )
        return
    
    if args.command == "temp":
        show_temp_files(
            details=args.details
        )
        return    

    if args.command == "clean":
        if args.clean_target == "packages":
            clean_pacman_cache(dry_run=args.dry_run)
            return

        if args.clean_target == "trash":
            clean_trash(dry_run=args.dry_run)
            return

        if args.clean_target == "yay":
            clean_yay(dry_run=args.dry_run)
            return

    show_disk_usage()
    show_pacman_cache()
    show_journal()
    show_yay_cache()    

if __name__ == "__main__":
    main()
