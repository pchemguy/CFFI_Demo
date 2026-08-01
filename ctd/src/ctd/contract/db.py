from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, TypeAlias
from enum import StrEnum


__all__ = (
    "CFFIModelDB",
    "attributes_insert",
)


PathLike: TypeAlias = str | Path | None
AttributeRow: TypeAlias = Mapping[str, Any]
AttributeRows: TypeAlias = AttributeRow | Iterable[AttributeRow]


class CTypeAttributes(StrEnum):
    NAME      = "name"
    CNAME     = "cname"
    KIND      = "kind"
    GROUP     = "group"
    ITEM      = "item"
    LENGTH    = "length"
    FIELDS    = "fields"
    ARGS      = "args"
    RESULT    = "result"
    ELLIPSIS  = "ellipsis"
    ABI       = "abi"
    ELEMENTS  = "elements"
    RELEMENTS = "relements"


def _normalize_value(value: Any) -> Any:
    """Convert unsupported SQLite values to strings.

    Values natively supported by ``sqlite3`` are preserved. Any other
    object is converted using ``str(value)``.
    """
    if value is None or isinstance(
        value,
        (str, int, float, bytes),
    ):
        return value

    return str(value)


def _coerce_rows(rows: AttributeRows) -> tuple[list[AttributeRow], bool]:
    """Return rows as a list and indicate whether one mapping was supplied."""
    if isinstance(rows, Mapping):
        return [rows], True

    if isinstance(rows, (str, bytes, bytearray)):
        raise TypeError(
            "attributes must be a mapping or an iterable of mappings"
        )

    try:
        result = list(rows)
    except TypeError as error:
        raise TypeError(
            "attributes must be a mapping or an iterable of mappings"
        ) from error

    return result, False


def _normalize_row(row: AttributeRow) -> dict[str, Any]:
    """Validate and normalize one attributes row."""
    if not isinstance(row, Mapping):
        raise TypeError(
            "Each attributes row must be a mapping, "
            f"not {type(row).__name__}"
        )

    normalized = {
        str(key): ._normalize_value(value)
        for key, value in row.items()
    }

    unknown_columns = normalized.keys() - [status.value for status in CTypeAttributes]
    if unknown_columns:
        columns = ", ".join(sorted(unknown_columns))
        raise ValueError(
            f"Unknown attributes column(s): {columns}"
        )

    if not normalized:
        raise ValueError("An attributes row cannot be empty")

    return normalized


class CFFIModelDB:
    """Manage the SQLite database containing the CFFI model.

    By default, the database and schema files are expected beside this script:

    - ``cffi_model.db``
    - ``schema.sql``

    If the database file does not exist, it is created and initialized by
    executing the complete contents of ``schema.sql``.
    """

    db_path: PathLike
    db: sqlite3.Connection | None

    def __init__(self, database: PathLike = None, schema: PathLike = None) -> None:
        """Open or create the CFFI model database.

        Args:
            database:
                SQLite database path. The default is ``cffi_model.db`` beside
                this script.
            schema:
                Schema file path. The default is ``schema.sql`` beside this
                script. It is used only when the database file does not exist.

        Raises:
            FileNotFoundError:
                If the database must be created but the schema file does not
                exist.
            sqlite3.Error:
                If the database cannot be opened or initialized.
        """
        script_directory = Path(__file__).resolve().parent

        self.db_path = (
            Path(database).expanduser().resolve()
            if database is not None
            else script_directory / "cffi_model.db"
        )
        self.schema_path = (
            Path(schema).expanduser().resolve()
            if schema is not None
            else script_directory / "schema.sql"
        )

        database_exists = self.db_path.exists()

        if not database_exists and not self.schema_path.is_file():
            raise FileNotFoundError(
                f"Schema file not found: {self.schema_path}"
            )

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db = sqlite3.connect(self.db_path)
        self.db.execute("PRAGMA foreign_keys = ON")

        try:
            if not database_exists:
                self._initialize_schema()
        except Exception:
            self.db.close()

            # Do not leave behind a partially initialized database.
            try:
                self.db_path.unlink(missing_ok=True)
            except OSError:
                pass

            raise

    def __enter__(self) -> CFFIModelDB:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object | None,
    ) -> None:
        if exception_type is None:
            self.db.commit()
        else:
            self.db.rollback()

        self.close()

    def close(self) -> None:
        """Close the instance database connection."""
        self.db.close()

    def _initialize_schema(self) -> None:
        """Initialize a newly created database from ``schema.sql``."""
        schema_sql = self.schema_path.read_text(encoding="utf-8")

        try:
            self.db.executescript(schema_sql)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def attributes_insert(
        self,
        attributes: AttributeRows,
        connection: sqlite3.Connection | None = None,
    ) -> int | list[int]:
        """Insert one or more rows into the ``attributes`` table.

        Args:
            attributes:
                A mapping representing one row, or an iterable of mappings.
                Dictionary keys must be valid ``attributes`` column names.
                Unsupported SQLite value objects are converted to strings.
            connection:
                Optional SQLite connection. When omitted, the connection owned
                by this instance is used.

        Returns:
            The inserted row ID when one mapping is supplied, or a list of row
            IDs when an iterable of mappings is supplied.

        Raises:
            TypeError:
                If the input or any row is not a mapping.
            ValueError:
                If a row is empty or contains unknown columns.
            sqlite3.Error:
                If SQLite rejects an insertion.
        """
        db = connection if connection is not None else self.db
        rows, single_row = _coerce_rows(attributes)

        inserted_ids: list[int] = []

        with db:
            for source_row in rows:
                row = _normalize_row(source_row)

                columns = tuple(row)
                placeholders = ", ".join("?" for _ in columns)
                column_sql = ", ".join(
                    f'"{column.replace(chr(34), chr(34) * 2)}"'
                    for column in columns
                )

                sql = (
                    f'INSERT INTO "attributes" ({column_sql}) '
                    f"VALUES ({placeholders})"
                )

                cursor = db.execute(
                    sql,
                    tuple(row[column] for column in columns),
                )

                if cursor.lastrowid is None:
                    raise sqlite3.DatabaseError(
                        "SQLite did not return an inserted row ID"
                    )

                inserted_ids.append(cursor.lastrowid)

        if single_row:
            return inserted_ids[0]

        return inserted_ids


def attributes_insert(
    attributes: AttributeRows,
    connection: sqlite3.Connection,
) -> int | list[int]:
    """Insert attributes using an explicitly supplied SQLite connection.

    This module-level convenience function follows the same input and return
    conventions as :meth:`CFFIModelDB.attributes_insert`.
    """
    rows, single_row = CFFIModelDB._coerce_rows(attributes)
    inserted_ids: list[int] = []

    with connection:
        for source_row in rows:
            row = CFFIModelDB._normalize_row(source_row)

            columns = tuple(row)
            placeholders = ", ".join("?" for _ in columns)
            column_sql = ", ".join(
                f'"{column.replace(chr(34), chr(34) * 2)}"'
                for column in columns
            )

            cursor = connection.execute(
                (
                    f'INSERT INTO "attributes" ({column_sql}) '
                    f"VALUES ({placeholders})"
                ),
                tuple(row[column] for column in columns),
            )

            if cursor.lastrowid is None:
                raise sqlite3.DatabaseError(
                    "SQLite did not return an inserted row ID"
                )

            inserted_ids.append(cursor.lastrowid)

    if single_row:
        return inserted_ids[0]

    return inserted_ids


def main() -> int:
    with CFFIModelDB() as database:
        database.attributes_insert(
            {
                "name": "example",
                "cname": "example_t",
                "kind": "type",
                "group": "demo",
            }
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
