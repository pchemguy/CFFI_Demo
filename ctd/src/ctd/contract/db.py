from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeAlias


__all__ = (
    "CFFIModelDB",
)


PathLike: TypeAlias = str | Path
AttributeRow: TypeAlias = Mapping[str, Any]
AttributeRows: TypeAlias = AttributeRow | Iterable[AttributeRow]


class CTypeAttributes(StrEnum):
    """Column names accepted by the ``attributes`` table."""

    ID        = "id"
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
    """Convert values unsupported by SQLite to strings.

    Values natively accepted by :mod:`sqlite3` are preserved. Any other object
    is converted by calling :class:`str`.
    """
    if value is None or isinstance(value, (str, int, float, bytes)):
        return value

    return str(value)


def _coerce_rows(rows: AttributeRows) -> tuple[list[AttributeRow], bool]:
    """Normalize the input into a list of rows.

    Returns:
        A pair containing the normalized row list and a flag indicating whether
        the caller supplied one mapping rather than an iterable of mappings.

    Raises:
        TypeError:
            If ``rows`` is neither a mapping nor an iterable of mappings.
        ValueError:
            If an empty iterable is supplied.
    """
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

    if not result:
        raise ValueError("attributes cannot be an empty iterable")

    return result, False


def _normalize_row(row: AttributeRow) -> dict[str, Any]:
    """Validate and normalize one ``attributes`` row.

    Raises:
        TypeError:
            If ``row`` is not a mapping.
        ValueError:
            If the mapping is empty or contains an unknown column name.
    """
    if not isinstance(row, Mapping):
        raise TypeError(
            "Each attributes row must be a mapping, "
            f"not {type(row).__name__}"
        )

    if not row:
        raise ValueError("An attributes row cannot be empty")

    normalized = {
        str(key): _normalize_value(value)
        for key, value in row.items()
    }

    unknown_columns = normalized.keys() - frozenset(CTypeAttributes)
    if unknown_columns:
        columns = ", ".join(sorted(unknown_columns))
        raise ValueError(f"Unknown attributes column(s): {columns}")

    return normalized


class CFFIModelDB:
    """Manage the SQLite database containing the CFFI model.

    By default, the database and schema files are located beside this module:

    - ``cffi_model.db``
    - ``schema.sql``

    If the database file does not exist, it is created and initialized by
    executing the complete contents of ``schema.sql``.
    """

    db_path: Path
    schema_path: Path
    db: sqlite3.Connection

    def __init__(
        self,
        database: PathLike | None = None,
        schema: PathLike | None = None,
    ) -> None:
        """Open or create the CFFI model database.

        Args:
            database:
                Database path. The default is ``cffi_model.db`` beside this
                module.
            schema:
                Schema path. The default is ``schema.sql`` beside this module.
                The schema is used only when the database file does not exist.

        Raises:
            FileNotFoundError:
                If a new database must be initialized but the schema file does
                not exist.
            sqlite3.Error:
                If SQLite cannot open or initialize the database.
        """
        module_directory = Path(__file__).resolve().parent

        self.db_path = (
            Path(database).expanduser().resolve()
            if database is not None
            else module_directory / "cffi_model.db"
        )
        self.schema_path = (
            Path(schema).expanduser().resolve()
            if schema is not None
            else module_directory / "schema.sql"
        )

        database_exists = self.db_path.exists()

        if not database_exists and not self.schema_path.is_file():
            raise FileNotFoundError(
                f"Schema file not found: {self.schema_path}"
            )

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db = sqlite3.connect(self.db_path)

        try:
            self.db.execute("PRAGMA foreign_keys = ON")

            if not database_exists:
                self._initialize_schema()
        except Exception:
            self.db.close()

            if not database_exists:
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
        """Close the database connection."""
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
        db: sqlite3.Connection | None = None,
    ) -> int | list[int]:
        """Insert one or more rows into the ``attributes`` table.

        Args:
            attributes:
                One mapping representing a row, or an iterable of mappings.
                Keys must correspond to columns declared by
                :class:`CTypeAttributes`. Values unsupported by SQLite are
                converted to strings.
            db:
                Optional SQLite connection. The instance connection is used
                when this argument is omitted.

        Returns:
            The inserted row ID when one mapping is supplied. When an iterable
            is supplied, returns the inserted row IDs in input order.

        Raises:
            TypeError:
                If the input or one of its rows is not a mapping.
            ValueError:
                If a row is empty, an iterable is empty, or a row contains an
                unknown column.
            sqlite3.Error:
                If SQLite rejects an insertion.
        """
        db = self.db if db is None else db

        rows, single_row = _coerce_rows(attributes)
        normalized_rows = [_normalize_row(row) for row in rows]

        inserted_ids: list[int] = []

        with db:
            for row in normalized_rows:
                columns = tuple(row)
                column_sql = ", ".join(f'"{column}"' for column in columns)
                placeholders = ", ".join("?" for _ in columns)

                cursor = db.execute(
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
    with CFFIModelDB():
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
