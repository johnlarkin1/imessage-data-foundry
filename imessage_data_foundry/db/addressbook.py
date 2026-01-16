import sqlite3
from pathlib import Path
from typing import Self

from imessage_data_foundry.db.schema import addressbook as schema
from imessage_data_foundry.personas.models import IdentifierType, Persona
from imessage_data_foundry.utils.names import parse_name


class AddressBookBuilder:
    def __init__(
        self,
        output_path: str | Path,
        in_memory: bool = False,
    ) -> None:
        self.output_path = Path(output_path)
        self.in_memory = in_memory

        self._connection: sqlite3.Connection | None = None
        self._finalized: bool = False

        self._next_record_pk: int = 1
        self._next_phone_pk: int = 1
        self._next_email_pk: int = 1

        self._persona_to_record: dict[str, int] = {}

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._initialize()
        return self._connection  # type: ignore[return-value]

    def _initialize(self) -> None:
        db_path = ":memory:" if self.in_memory else str(self.output_path)

        if not self.in_memory:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        for table_sql in schema.get_tables().values():
            self.connection.execute(table_sql)
        for index_sql in schema.get_indexes():
            self.connection.execute(index_sql)
        self.connection.commit()

    def add_contact(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
        nickname: str | None = None,
        unique_id: str | None = None,
    ) -> int:
        pk = self._next_record_pk
        self._next_record_pk += 1

        self.connection.execute(
            """
            INSERT INTO ZABCDRECORD (Z_PK, ZUNIQUEID, ZFIRSTNAME, ZLASTNAME, ZMIDDLENAME, ZNICKNAME)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pk, unique_id, first_name, last_name, middle_name, nickname),
        )
        return pk

    def add_contact_from_persona(self, persona: Persona) -> int:
        if persona.id in self._persona_to_record:
            return self._persona_to_record[persona.id]

        first_name, middle_name, last_name = parse_name(persona.name)

        if first_name is None and last_name is None:
            first_name = persona.identifier

        unique_id = f"AB-{persona.id}"
        pk = self.add_contact(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            unique_id=unique_id,
        )

        if persona.identifier_type == IdentifierType.PHONE:
            self.add_phone_number(pk, persona.identifier)
        else:
            self.add_email_address(pk, persona.identifier)

        self._persona_to_record[persona.id] = pk
        return pk

    def add_phone_number(
        self,
        owner_pk: int,
        full_number: str,
        label: str = "_$!<Mobile>!$_",
    ) -> int:
        pk = self._next_phone_pk
        self._next_phone_pk += 1

        self.connection.execute(
            """
            INSERT INTO ZABCDPHONENUMBER (Z_PK, ZOWNER, ZFULLNUMBER, ZLABEL)
            VALUES (?, ?, ?, ?)
            """,
            (pk, owner_pk, full_number, label),
        )
        return pk

    def add_email_address(
        self,
        owner_pk: int,
        address: str,
        label: str = "_$!<Home>!$_",
    ) -> int:
        pk = self._next_email_pk
        self._next_email_pk += 1

        self.connection.execute(
            """
            INSERT INTO ZABCDEMAILADDRESS (Z_PK, ZOWNER, ZADDRESS, ZLABEL)
            VALUES (?, ?, ?, ?)
            """,
            (pk, owner_pk, address, label),
        )
        return pk

    def add_all_personas(self, personas: list[Persona]) -> dict[str, int]:
        mapping: dict[str, int] = {}
        for persona in personas:
            pk = self.add_contact_from_persona(persona)
            mapping[persona.id] = pk
        return mapping

    def commit(self) -> None:
        self.connection.commit()

    def finalize(self) -> Path:
        if self._finalized:
            raise RuntimeError("AddressBook database already finalized")

        self.connection.commit()

        if self.in_memory:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            file_conn = sqlite3.connect(str(self.output_path))
            self.connection.backup(file_conn)
            file_conn.close()

        self._finalized = True
        return self.output_path

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    @property
    def contact_count(self) -> int:
        return len(self._persona_to_record)

    @property
    def phone_count(self) -> int:
        return self._next_phone_pk - 1

    @property
    def email_count(self) -> int:
        return self._next_email_pk - 1

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._finalized and exc_type is None:
            self.finalize()
        self.close()
