import platform
import subprocess

from imessage_data_foundry.db.schema import sequoia, sonoma, tahoe
from imessage_data_foundry.db.schema.base import SchemaVersion

VERSION_MAP: dict[int, SchemaVersion] = {
    14: SchemaVersion.SONOMA,
    15: SchemaVersion.SEQUOIA,
    26: SchemaVersion.TAHOE,
}


def get_macos_version() -> str | None:
    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def get_major_version(version_string: str) -> int:
    try:
        return int(version_string.split(".")[0])
    except (ValueError, IndexError):
        return 0


def detect_schema_version() -> SchemaVersion:
    version = get_macos_version()
    if not version:
        return SchemaVersion.SEQUOIA

    major = get_major_version(version)
    return VERSION_MAP.get(major, SchemaVersion.SEQUOIA)


def get_schema_for_version(version: str | SchemaVersion) -> SchemaVersion:
    if isinstance(version, SchemaVersion):
        return version
    try:
        return SchemaVersion(version.lower())
    except ValueError:
        pass
    major = get_major_version(version)
    return VERSION_MAP.get(major, SchemaVersion.SEQUOIA)


def get_schema_module(version: SchemaVersion):
    match version:
        case SchemaVersion.SEQUOIA:
            return sequoia
        case SchemaVersion.SONOMA:
            return sonoma
        case SchemaVersion.TAHOE:
            return tahoe
        case _:
            raise ValueError(f"Unknown schema version: {version}")
