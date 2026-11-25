from __future__ import annotations
from dataclasses import dataclass
from .DBMgr import DBMgr

def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'

@dataclass
class Column:
    name: str
    type: str

class TBLSchema:
    def __init__(self, name: str) -> None:
        self.table_name = name
        self.columns: list[Column] = []
        self.unique_keys: list[list[str]] = []

    def add_column(self, name: str, type: str) -> None:
        self.columns.append(Column(name, type))

    def add_unique(self, cols: list[str]) -> None:
        self.unique_keys.append(cols)

    def generate_sql(self) -> str:
        definitions: list[str] = []

        for column in self.columns:
            definitions.append(
                f"{quote_identifier(column.name)} {column.type}"
            )

        for cols in self.unique_keys:
            columns = ", ".join(
                quote_identifier(column) for column in cols
            )
            definitions.append(f"UNIQUE({columns})")

        body = ", ".join(definitions)

        return (
            f"CREATE TABLE IF NOT EXISTS "
            f"{quote_identifier(self.table_name)} ({body});"
        )

    def create(self, db: DBMgr) -> None:
        db.execute(self.generate_sql())