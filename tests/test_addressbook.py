import sqlite3
from pathlib import Path

from imessage_data_foundry.db.addressbook import AddressBookBuilder
from imessage_data_foundry.db.validators import (
    validate_addressbook,
    validate_addressbook_foreign_keys,
    validate_addressbook_schema,
)
from imessage_data_foundry.personas.models import IdentifierType, Persona


class TestAddressBookBuilderInit:
    def test_creates_database_file(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path):
            pass
        assert db_path.exists()

    def test_creates_parent_directory(self, tmp_path: Path):
        db_path = tmp_path / "subdir" / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            builder.add_contact(first_name="John")
        assert db_path.exists()


class TestAddressBookBuilderContextManager:
    def test_finalizes_on_exit(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            builder.add_contact(first_name="John", last_name="Doe")

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM ZABCDRECORD")
        assert cursor.fetchone()[0] == 1
        conn.close()


class TestAddContact:
    def test_returns_pk(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact(first_name="John")
            assert pk == 1

    def test_increments_pk(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            pk1 = builder.add_contact(first_name="John")
            pk2 = builder.add_contact(first_name="Jane")
            assert pk1 == 1
            assert pk2 == 2

    def test_stores_all_fields(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            builder.add_contact(
                first_name="John",
                last_name="Doe",
                middle_name="Michael",
                nickname="Johnny",
                unique_id="AB-12345",
            )
            cursor = builder.connection.execute(
                "SELECT ZFIRSTNAME, ZLASTNAME, ZMIDDLENAME, ZNICKNAME, ZUNIQUEID FROM ZABCDRECORD WHERE Z_PK = 1"
            )
            row = cursor.fetchone()
            assert row[0] == "John"
            assert row[1] == "Doe"
            assert row[2] == "Michael"
            assert row[3] == "Johnny"
            assert row[4] == "AB-12345"


class TestAddContactFromPersona:
    def test_parses_two_part_name(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="John Doe",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
        )
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact_from_persona(persona)
            cursor = builder.connection.execute(
                "SELECT ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD WHERE Z_PK = ?", (pk,)
            )
            row = cursor.fetchone()
            assert row[0] == "John"
            assert row[1] == "Doe"

    def test_parses_single_name(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="Madonna",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
        )
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact_from_persona(persona)
            cursor = builder.connection.execute(
                "SELECT ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD WHERE Z_PK = ?", (pk,)
            )
            row = cursor.fetchone()
            assert row[0] == "Madonna"
            assert row[1] is None

    def test_parses_three_part_name(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="John Michael Doe",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
        )
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact_from_persona(persona)
            cursor = builder.connection.execute(
                "SELECT ZFIRSTNAME, ZMIDDLENAME, ZLASTNAME FROM ZABCDRECORD WHERE Z_PK = ?",
                (pk,),
            )
            row = cursor.fetchone()
            assert row[0] == "John"
            assert row[1] == "Michael"
            assert row[2] == "Doe"

    def test_adds_phone_for_phone_persona(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="John Doe",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
        )
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact_from_persona(persona)
            cursor = builder.connection.execute(
                "SELECT ZFULLNUMBER FROM ZABCDPHONENUMBER WHERE ZOWNER = ?", (pk,)
            )
            row = cursor.fetchone()
            assert row[0] == "+15551234567"

    def test_adds_email_for_email_persona(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="John Doe",
            identifier="john@example.com",
            identifier_type=IdentifierType.EMAIL,
        )
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact_from_persona(persona)
            cursor = builder.connection.execute(
                "SELECT ZADDRESS FROM ZABCDEMAILADDRESS WHERE ZOWNER = ?", (pk,)
            )
            row = cursor.fetchone()
            assert row[0] == "john@example.com"

    def test_uses_persona_id_for_unique_id(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="John Doe",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
        )
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact_from_persona(persona)
            cursor = builder.connection.execute(
                "SELECT ZUNIQUEID FROM ZABCDRECORD WHERE Z_PK = ?", (pk,)
            )
            row = cursor.fetchone()
            assert row[0] == f"AB-{persona.id}"

    def test_deduplicates_same_persona(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        persona = Persona(
            name="John Doe",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
        )
        with AddressBookBuilder(db_path) as builder:
            pk1 = builder.add_contact_from_persona(persona)
            pk2 = builder.add_contact_from_persona(persona)
            assert pk1 == pk2
            assert builder.contact_count == 1


class TestAddPhoneNumber:
    def test_creates_phone_record(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            contact_pk = builder.add_contact(first_name="John")
            phone_pk = builder.add_phone_number(contact_pk, "(415) 555-1234")

            cursor = builder.connection.execute(
                "SELECT ZOWNER, ZFULLNUMBER, ZLABEL FROM ZABCDPHONENUMBER WHERE Z_PK = ?",
                (phone_pk,),
            )
            row = cursor.fetchone()
            assert row[0] == contact_pk
            assert row[1] == "(415) 555-1234"
            assert row[2] == "_$!<Mobile>!$_"


class TestAddEmailAddress:
    def test_creates_email_record(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            contact_pk = builder.add_contact(first_name="John")
            email_pk = builder.add_email_address(contact_pk, "john@example.com")

            cursor = builder.connection.execute(
                "SELECT ZOWNER, ZADDRESS, ZLABEL FROM ZABCDEMAILADDRESS WHERE Z_PK = ?",
                (email_pk,),
            )
            row = cursor.fetchone()
            assert row[0] == contact_pk
            assert row[1] == "john@example.com"
            assert row[2] == "_$!<Home>!$_"


class TestAddAllPersonas:
    def test_adds_multiple_personas(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        personas = [
            Persona(
                name="John Doe",
                identifier="+15551234567",
                identifier_type=IdentifierType.PHONE,
            ),
            Persona(
                name="Jane Smith",
                identifier="jane@example.com",
                identifier_type=IdentifierType.EMAIL,
            ),
        ]
        with AddressBookBuilder(db_path) as builder:
            mapping = builder.add_all_personas(personas)
            assert len(mapping) == 2
            assert builder.contact_count == 2


class TestAddressBookBuilderCounts:
    def test_contact_count(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            persona = Persona(
                name="John Doe",
                identifier="+15551234567",
                identifier_type=IdentifierType.PHONE,
            )
            builder.add_contact_from_persona(persona)
            assert builder.contact_count == 1

    def test_phone_count(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact(first_name="John")
            builder.add_phone_number(pk, "+15551234567")
            builder.add_phone_number(pk, "+15559876543")
            assert builder.phone_count == 2

    def test_email_count(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact(first_name="John")
            builder.add_email_address(pk, "john@example.com")
            assert builder.email_count == 1


class TestAddressBookValidation:
    def test_valid_addressbook_passes(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            pk = builder.add_contact(first_name="John", last_name="Doe")
            builder.add_phone_number(pk, "+15551234567")

        result = validate_addressbook(db_path)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_schema_validation_passes(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path):
            pass

        result = validate_addressbook_schema(db_path)
        assert result.is_valid

    def test_missing_table_fails(self, tmp_path: Path):
        db_path = tmp_path / "bad.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE ZABCDRECORD (Z_PK INTEGER PRIMARY KEY)")
        conn.close()

        result = validate_addressbook_schema(db_path)
        assert not result.is_valid
        assert any("ZABCDPHONENUMBER" in e for e in result.errors)

    def test_orphaned_phone_fails(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path) as builder:
            builder.connection.execute(
                "INSERT INTO ZABCDPHONENUMBER (Z_PK, ZOWNER, ZFULLNUMBER) VALUES (1, 999, '+15551234567')"
            )
            builder.commit()

        result = validate_addressbook_foreign_keys(db_path)
        assert not result.is_valid
        assert any("invalid ZOWNER" in e for e in result.errors)


class TestInMemoryAddressBook:
    def test_in_memory_then_write(self, tmp_path: Path):
        db_path = tmp_path / "addressbook.db"
        with AddressBookBuilder(db_path, in_memory=True) as builder:
            builder.add_contact(first_name="John", last_name="Doe")

        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM ZABCDRECORD")
        assert cursor.fetchone()[0] == 1
        conn.close()
