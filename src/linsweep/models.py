from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RiskLevel(Enum):
    SAFE = "safe"
    REVIEW = "review"
    DANGEROUS = "dangerous"
    UNKNOWN = "unknown"

class PackageStatus(Enum):
    INSTALLED = "installed"
    BACKUP = "backup"
    OLD = "old"
    NEWER = "newer"
    NOT_INSTALLED = "not_installed"

@dataclass
class CleanupCandidate:
    name: str
    path: Path
    size_bytes: int
    description: str
    risk: RiskLevel

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 ** 2)

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)

@dataclass
class CachedPackage:
    name: str
    version: str
    architecture: str
    path: Path
    size_bytes: int
    status: PackageStatus | None = None

    @property
    def full_version(self) -> str:
        return self.version

@dataclass
class YayCacheEntry:
    name: str
    path: Path
    total_size: int

    compiled_current_size: int = 0
    compiled_old_size: int = 0
    compiled_newer_size: int = 0
    compiled_not_installed_size: int = 0

    downloaded_sources_size: int = 0
    git_size: int = 0
    metadata_size: int = 0
    other_size: int = 0

    compiled_current_count: int = 0
    compiled_old_count: int = 0
    compiled_newer_count: int = 0
    compiled_not_installed_count: int = 0

@dataclass
class OrphanPackage:
    name: str
    version: str
    size_bytes: int

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 ** 2)
