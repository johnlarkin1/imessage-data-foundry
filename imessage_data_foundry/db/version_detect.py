"""macOS version detection for schema selection."""

import platform
import subprocess

from imessage_data_foundry.db.schema.base import SchemaVersion

VERSION_MAP: dict[int, SchemaVersion] = {
    14: SchemaVersion.SONOMA,
    15: SchemaVersion.SEQUOIA,
    26: SchemaVersion.TAHOE,
}


def get_macos_version() -> str | None:
    """Get the current macOS version string (e.g., '15.1.0').

    Returns None if not on macOS or version cannot be determined.
    """
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
    """Extract major version number from version string.

    Args:
        version_string: Version string like "15.1.0"

    Returns:
        Major version number (e.g., 15) or 0 if parsing fails
    """
    try:
        return int(version_string.split(".")[0])
    except (ValueError, IndexError):
        return 0


def detect_schema_version() -> SchemaVersion:
    """Detect the appropriate schema version for the current macOS.

    Returns SchemaVersion.SEQUOIA as default if detection fails or not on macOS.
    """
    version = get_macos_version()
    if not version:
        return SchemaVersion.SEQUOIA

    major = get_major_version(version)
    return VERSION_MAP.get(major, SchemaVersion.SEQUOIA)


def get_schema_for_version(version: str | SchemaVersion) -> SchemaVersion:
    """Convert a version string or SchemaVersion to a SchemaVersion enum.

    Args:
        version: Either a SchemaVersion enum, a version name ("sequoia"),
                 or a macOS version string ("15.1.0")

    Returns:
        SchemaVersion enum value
    """
    if isinstance(version, SchemaVersion):
        return version

    # Try as version name (e.g., "sequoia", "sonoma")
    try:
        return SchemaVersion(version.lower())
    except ValueError:
        pass

    # Try as macOS version string (e.g., "15.1.0", "14.5")
    major = get_major_version(version)
    return VERSION_MAP.get(major, SchemaVersion.SEQUOIA)


def get_schema_module(version: SchemaVersion):
    """Import and return the appropriate schema module.

    Args:
        version: SchemaVersion enum value

    Returns:
        The schema module (sequoia, sonoma, or tahoe)

    Raises:
        ValueError: If version is not recognized
    """
    if version == SchemaVersion.SEQUOIA:
        from imessage_data_foundry.db.schema import sequoia

        return sequoia
    elif version == SchemaVersion.SONOMA:
        from imessage_data_foundry.db.schema import sonoma

        return sonoma
    elif version == SchemaVersion.TAHOE:
        from imessage_data_foundry.db.schema import tahoe

        return tahoe
    raise ValueError(f"Unknown schema version: {version}")
