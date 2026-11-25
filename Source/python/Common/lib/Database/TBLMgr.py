from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from HG.Common.Database import DBMgr

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


class TBLMgr:
    def __init__(self, database: Database, table_name: str) -> None:
        self.database = database
        self.table_name = table_name
        self._quoted_table = quote_identifier(table_name)

    def insert(self, values: Mapping[str, Any]) -> int:
        if not values:
            raise ValueError("values must not be empty")

        columns = list(values)
        column_sql = ", ".join(quote_identifier(column) for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        sql = (
            f"INSERT INTO {self._quoted_table} ({column_sql}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT DO NOTHING"
        )
        # for i, column in enumerate(columns):
        #     print(
        #         i + 1,
        #         column,
        #         type(values[column]),
        #         values[column] if isinstance(values[column], (dict, list)) else ""
        #     )
        cursor = self.database.execute(sql, tuple(values[column] for column in columns))
        return cursor.lastrowid

    def insert_many(self, rows: Sequence[Mapping[str, Any]]) -> None:
        if not rows:
            return

        columns = list(rows[0])
        if not columns:
            raise ValueError("rows must contain at least one column")

        expected = set(columns)
        if any(set(row) != expected for row in rows):
            raise ValueError("all rows must contain the same columns")

        column_sql = ", ".join(quote_identifier(column) for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        sql = (
            f"INSERT INTO {self._quoted_table} ({column_sql}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT DO NOTHING"
        )
        parameters = [tuple(row[column] for column in columns) for row in rows]

        with self.database.transaction():
            self.database.execute_many(sql, parameters)

    def select(
        self,
        columns: Sequence[str] | None = None,
        where: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if columns:
            selected = ", ".join(quote_identifier(column) for column in columns)
        else:
            selected = "*"

        sql = f"SELECT {selected} FROM {self._quoted_table}"
        params: list[Any] = []

        if where:
            conditions = []
            for column, value in where.items():
                conditions.append(f"{quote_identifier(column)} = ?")
                params.append(value)
            sql += " WHERE " + " AND ".join(conditions)

        return self.database.query(sql, params)

    def select_cond_and(
        self,
        columns: Sequence[str] | None = None,
        where: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if columns:
            selected = ", ".join(quote_identifier(column) for column in columns)
        else:
            selected = "*"

        sql = f"SELECT {selected} FROM {self._quoted_table}"
        params: list[Any] = []

        if where:
            conditions = []

            for column, value in where.items():
                if isinstance(value, tuple):
                    op, val = value
                    conditions.append(
                        f"{quote_identifier(column)} {op} ?"
                    )
                    params.append(val)
                else:
                    conditions.append(
                        f"{quote_identifier(column)} = ?"
                    )
                    params.append(value)

            sql += " WHERE " + " AND ".join(conditions)

        return self.database.query(sql, params)
