import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another ValidationResult into this one."""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


@dataclass
class TableInfo:
    name: str
    columns: dict[str, str]  # column_name -> type
    row_count: int


def get_table_info(conn: sqlite3.Connection, table_name: str) -> TableInfo:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
    row_count = cursor.fetchone()[0]

    return TableInfo(name=table_name, columns=columns, row_count=row_count)


def get_all_tables(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def get_all_indexes(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def validate_schema(db_path: str | Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Failed to open database: {e}"],
        )

    try:
        tables = get_all_tables(conn)

        required_tables = [
            "message",
            "handle",
            "chat",
            "attachment",
            "chat_handle_join",
            "chat_message_join",
            "message_attachment_join",
            "_SqliteDatabaseProperties",
            "deleted_messages",
        ]

        for table in required_tables:
            if table not in tables:
                errors.append(f"Missing required table: {table}")

        if "message" in tables:
            msg_info = get_table_info(conn, "message")
            required_msg_cols = [
                "ROWID",
                "guid",
                "text",
                "handle_id",
                "service",
                "date",
                "is_from_me",
                "is_sent",
                "is_delivered",
            ]
            for col in required_msg_cols:
                if col not in msg_info.columns:
                    errors.append(f"message table missing column: {col}")

        if "handle" in tables:
            handle_info = get_table_info(conn, "handle")
            required_handle_cols = ["ROWID", "id", "service"]
            for col in required_handle_cols:
                if col not in handle_info.columns:
                    errors.append(f"handle table missing column: {col}")

        if "chat" in tables:
            chat_info = get_table_info(conn, "chat")
            required_chat_cols = [
                "ROWID",
                "guid",
                "style",
                "chat_identifier",
                "service_name",
            ]
            for col in required_chat_cols:
                if col not in chat_info.columns:
                    errors.append(f"chat table missing column: {col}")

        if "chat_message_join" in tables:
            cmj_info = get_table_info(conn, "chat_message_join")
            if "chat_id" not in cmj_info.columns:
                errors.append("chat_message_join missing chat_id column")
            if "message_id" not in cmj_info.columns:
                errors.append("chat_message_join missing message_id column")

        if "chat_handle_join" in tables:
            chj_info = get_table_info(conn, "chat_handle_join")
            if "chat_id" not in chj_info.columns:
                errors.append("chat_handle_join missing chat_id column")
            if "handle_id" not in chj_info.columns:
                errors.append("chat_handle_join missing handle_id column")

        indexes = get_all_indexes(conn)
        expected_indexes = [
            "message_idx_handle",
            "message_idx_date",
            "chat_idx_chat_identifier",
        ]
        for idx in expected_indexes:
            if idx not in indexes:
                warnings.append(f"Missing recommended index: {idx}")

    finally:
        conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_foreign_keys(db_path: str | Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    conn = sqlite3.connect(str(db_path))

    try:
        cursor = conn.execute(
            """
            SELECT m.ROWID, m.handle_id
            FROM message m
            WHERE m.handle_id > 0
            AND m.handle_id NOT IN (SELECT ROWID FROM handle)
        """
        )
        orphaned = cursor.fetchall()
        if orphaned:
            errors.append(f"Found {len(orphaned)} messages with invalid handle_id")

        cursor = conn.execute(
            """
            SELECT cmj.chat_id, cmj.message_id
            FROM chat_message_join cmj
            WHERE cmj.chat_id NOT IN (SELECT ROWID FROM chat)
            OR cmj.message_id NOT IN (SELECT ROWID FROM message)
        """
        )
        orphaned_joins = cursor.fetchall()
        if orphaned_joins:
            errors.append(f"Found {len(orphaned_joins)} invalid chat_message_join entries")

        cursor = conn.execute(
            """
            SELECT chj.chat_id, chj.handle_id
            FROM chat_handle_join chj
            WHERE chj.chat_id NOT IN (SELECT ROWID FROM chat)
            OR chj.handle_id NOT IN (SELECT ROWID FROM handle)
        """
        )
        orphaned_handle_joins = cursor.fetchall()
        if orphaned_handle_joins:
            errors.append(f"Found {len(orphaned_handle_joins)} invalid chat_handle_join entries")

        cursor = conn.execute(
            """
            SELECT maj.message_id, maj.attachment_id
            FROM message_attachment_join maj
            WHERE maj.message_id NOT IN (SELECT ROWID FROM message)
            OR maj.attachment_id NOT IN (SELECT ROWID FROM attachment)
        """
        )
        orphaned_att_joins = cursor.fetchall()
        if orphaned_att_joins:
            errors.append(
                f"Found {len(orphaned_att_joins)} invalid message_attachment_join entries"
            )

    finally:
        conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_guid_uniqueness(db_path: str | Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    conn = sqlite3.connect(str(db_path))

    try:
        cursor = conn.execute(
            """
            SELECT guid, COUNT(*) as cnt
            FROM message
            GROUP BY guid
            HAVING cnt > 1
        """
        )
        dupes = cursor.fetchall()
        if dupes:
            errors.append(f"Found {len(dupes)} duplicate message GUIDs")

        cursor = conn.execute(
            """
            SELECT guid, COUNT(*) as cnt
            FROM chat
            GROUP BY guid
            HAVING cnt > 1
        """
        )
        dupes = cursor.fetchall()
        if dupes:
            errors.append(f"Found {len(dupes)} duplicate chat GUIDs")

        cursor = conn.execute(
            """
            SELECT guid, COUNT(*) as cnt
            FROM attachment
            GROUP BY guid
            HAVING cnt > 1
        """
        )
        dupes = cursor.fetchall()
        if dupes:
            errors.append(f"Found {len(dupes)} duplicate attachment GUIDs")

    finally:
        conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_database(db_path: str | Path) -> ValidationResult:
    result = ValidationResult(is_valid=True)

    schema_result = validate_schema(db_path)
    result = result.merge(schema_result)

    if schema_result.is_valid:
        fk_result = validate_foreign_keys(db_path)
        result = result.merge(fk_result)

        guid_result = validate_guid_uniqueness(db_path)
        result = result.merge(guid_result)

    return result


def compare_schemas(
    generated_path: str | Path,
    reference_path: str | Path,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    gen_conn = sqlite3.connect(str(generated_path))
    ref_conn = sqlite3.connect(str(reference_path))

    try:
        gen_tables = set(get_all_tables(gen_conn))
        ref_tables = set(get_all_tables(ref_conn))

        missing = ref_tables - gen_tables
        extra = gen_tables - ref_tables

        for table in missing:
            if not table.startswith("sqlite_"):
                errors.append(f"Missing table from reference: {table}")

        for table in extra:
            if not table.startswith("sqlite_"):
                warnings.append(f"Extra table not in reference: {table}")

        for table in gen_tables & ref_tables:
            if table.startswith("sqlite_"):
                continue

            gen_info = get_table_info(gen_conn, table)
            ref_info = get_table_info(ref_conn, table)

            missing_cols = set(ref_info.columns.keys()) - set(gen_info.columns.keys())
            extra_cols = set(gen_info.columns.keys()) - set(ref_info.columns.keys())

            for col in missing_cols:
                warnings.append(f"Table {table} missing column: {col}")

            for col in extra_cols:
                warnings.append(f"Table {table} has extra column: {col}")

    finally:
        gen_conn.close()
        ref_conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def run_integrity_check(db_path: str | Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    conn = sqlite3.connect(str(db_path))

    try:
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        if result != "ok":
            errors.append(f"SQLite integrity check failed: {result}")
    finally:
        conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_addressbook_schema(db_path: str | Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Failed to open AddressBook database: {e}"],
        )

    try:
        tables = get_all_tables(conn)

        required_tables = ["ZABCDRECORD", "ZABCDPHONENUMBER", "ZABCDEMAILADDRESS"]

        for table in required_tables:
            if table not in tables:
                errors.append(f"Missing required table: {table}")

        if "ZABCDRECORD" in tables:
            record_info = get_table_info(conn, "ZABCDRECORD")
            required_cols = ["Z_PK", "ZFIRSTNAME", "ZLASTNAME", "ZMIDDLENAME", "ZNICKNAME"]
            for col in required_cols:
                if col not in record_info.columns:
                    errors.append(f"ZABCDRECORD missing column: {col}")

        if "ZABCDPHONENUMBER" in tables:
            phone_info = get_table_info(conn, "ZABCDPHONENUMBER")
            required_cols = ["Z_PK", "ZOWNER", "ZFULLNUMBER"]
            for col in required_cols:
                if col not in phone_info.columns:
                    errors.append(f"ZABCDPHONENUMBER missing column: {col}")

        if "ZABCDEMAILADDRESS" in tables:
            email_info = get_table_info(conn, "ZABCDEMAILADDRESS")
            required_cols = ["Z_PK", "ZOWNER", "ZADDRESS"]
            for col in required_cols:
                if col not in email_info.columns:
                    errors.append(f"ZABCDEMAILADDRESS missing column: {col}")

        indexes = get_all_indexes(conn)
        expected_indexes = [
            "ZABCDPHONENUMBER_ZOWNER_INDEX",
            "ZABCDEMAILADDRESS_ZOWNER_INDEX",
        ]
        for idx in expected_indexes:
            if idx not in indexes:
                warnings.append(f"Missing recommended index: {idx}")

    finally:
        conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_addressbook_foreign_keys(db_path: str | Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    conn = sqlite3.connect(str(db_path))

    try:
        cursor = conn.execute(
            """
            SELECT Z_PK, ZOWNER
            FROM ZABCDPHONENUMBER
            WHERE ZOWNER NOT IN (SELECT Z_PK FROM ZABCDRECORD)
        """
        )
        orphaned = cursor.fetchall()
        if orphaned:
            errors.append(f"Found {len(orphaned)} phone numbers with invalid ZOWNER")

        cursor = conn.execute(
            """
            SELECT Z_PK, ZOWNER
            FROM ZABCDEMAILADDRESS
            WHERE ZOWNER NOT IN (SELECT Z_PK FROM ZABCDRECORD)
        """
        )
        orphaned_emails = cursor.fetchall()
        if orphaned_emails:
            errors.append(f"Found {len(orphaned_emails)} email addresses with invalid ZOWNER")

    finally:
        conn.close()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_addressbook(db_path: str | Path) -> ValidationResult:
    result = ValidationResult(is_valid=True)

    schema_result = validate_addressbook_schema(db_path)
    result = result.merge(schema_result)

    if schema_result.is_valid:
        fk_result = validate_addressbook_foreign_keys(db_path)
        result = result.merge(fk_result)

    return result
