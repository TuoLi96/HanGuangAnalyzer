from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .DBMgr import DBMgr

SqlParams = Sequence[Any] | Mapping[str, Any]

class DynamicTBLMgr:
    def __init__(self, db: DBMgr, table: str) -> None:
        self.db_mgr = db
        self.table_name = table

    def insert(self, record: Mapping[str, Any]) -> bool:
        if not record:
            return False

        columns = list(record.keys())
        values = list(record.values())

        cols = ",".join(columns)
        placeholders = ",".join(["?"] * len(columns))

        sql = f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholders})"

        try:
            self.db_mgr.execute(sql, values)
            return True
        except Exception:
            return False

    def select(
        self,
        columns: Sequence[str] | None = None,
        where: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if columns:
            selected = ", ".join(quote_identifier(column) for column in columns)
        else:
            selected = "*"

        sql = f"SELECT {selected} FROM {self.table_name}"
        params: list[Any] = []

        if where:
            conditions = []

            for column, value in where.items():
                if isinstance(value, tuple):
                    op, val = value
                    conditions.append(f"{quote_identifier(column)} {op} ?")
                    params.append(val)
                else:
                    conditions.append(f"{quote_identifier(column)} = ?")
                    params.append(value)

            sql += " WHERE " + " AND ".join(conditions)

        return self.db_mgr.query(sql, params)