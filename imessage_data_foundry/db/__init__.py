from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.db.schema.base import SchemaVersion
from imessage_data_foundry.db.validators import (
    ValidationResult,
    compare_schemas,
    validate_database,
    validate_foreign_keys,
    validate_guid_uniqueness,
    validate_schema,
)
from imessage_data_foundry.db.version_detect import (
    detect_schema_version,
    get_macos_version,
    get_schema_for_version,
)

__all__ = [
    "DatabaseBuilder",
    "SchemaVersion",
    "ValidationResult",
    "compare_schemas",
    "detect_schema_version",
    "get_macos_version",
    "get_schema_for_version",
    "validate_database",
    "validate_foreign_keys",
    "validate_guid_uniqueness",
    "validate_schema",
]
