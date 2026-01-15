from imessage_data_foundry.db.schema.base import SchemaVersion
from imessage_data_foundry.db.version_detect import (
    detect_schema_version,
    get_major_version,
    get_schema_for_version,
    get_schema_module,
)


class TestGetMajorVersion:
    def test_full_version(self):
        assert get_major_version("15.1.0") == 15

    def test_two_part_version(self):
        assert get_major_version("14.5") == 14

    def test_single_number(self):
        assert get_major_version("26") == 26

    def test_invalid_returns_zero(self):
        assert get_major_version("invalid") == 0

    def test_empty_returns_zero(self):
        assert get_major_version("") == 0


class TestDetectSchemaVersion:
    def test_returns_valid_version(self):
        version = detect_schema_version()
        assert version in [SchemaVersion.SONOMA, SchemaVersion.SEQUOIA, SchemaVersion.TAHOE]


class TestGetSchemaForVersion:
    def test_schema_version_passthrough(self):
        result = get_schema_for_version(SchemaVersion.SEQUOIA)
        assert result == SchemaVersion.SEQUOIA

    def test_version_name_lowercase(self):
        result = get_schema_for_version("sequoia")
        assert result == SchemaVersion.SEQUOIA

    def test_version_name_uppercase(self):
        result = get_schema_for_version("SONOMA")
        assert result == SchemaVersion.SONOMA

    def test_macos_version_string_15(self):
        result = get_schema_for_version("15.1.0")
        assert result == SchemaVersion.SEQUOIA

    def test_macos_version_string_14(self):
        result = get_schema_for_version("14.5")
        assert result == SchemaVersion.SONOMA

    def test_macos_version_string_26(self):
        result = get_schema_for_version("26.0")
        assert result == SchemaVersion.TAHOE

    def test_unknown_version_defaults_to_sequoia(self):
        result = get_schema_for_version("99.0.0")
        assert result == SchemaVersion.SEQUOIA


class TestGetSchemaModule:
    def test_sequoia_module(self):
        module = get_schema_module(SchemaVersion.SEQUOIA)
        assert module.SCHEMA_VERSION == "sequoia"
        assert callable(module.get_tables)
        assert callable(module.get_indexes)

    def test_sonoma_module(self):
        module = get_schema_module(SchemaVersion.SONOMA)
        assert module.SCHEMA_VERSION == "sonoma"

    def test_tahoe_module(self):
        module = get_schema_module(SchemaVersion.TAHOE)
        assert module.SCHEMA_VERSION == "tahoe"

    def test_modules_have_required_exports(self):
        for version in SchemaVersion:
            module = get_schema_module(version)
            assert hasattr(module, "SCHEMA_VERSION")
            assert hasattr(module, "MACOS_VERSIONS")
            assert hasattr(module, "get_tables")
            assert hasattr(module, "get_indexes")
            assert hasattr(module, "get_triggers")
            assert hasattr(module, "get_metadata")
