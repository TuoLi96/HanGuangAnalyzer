from __future__ import annotations

from typing import Any

from HG.Common.Database import TBLSchema
from HG.Common.Database import TBLSchemaBuilder


class TSSchemaBuilder(TBLSchemaBuilder):
    def build(self, data: dict[str, Any]) -> TBLSchema:
        bug = data["bug"]
        table = bug["tbl"]

        schema = TBLSchema(table)

        schema.add_column(
            "id",
            "INTEGER PRIMARY KEY AUTOINCREMENT",
        )

        schema.add_column(
            "name",
            "TEXT",
        )

        unique_cols: list[str] = []

        for action in bug["key_actions"]:
            cols = [
                f"{action}_name",
                f"{action}_src_file",
                f"{action}_func_name",
                f"{action}_var_name",
                f"{action}_line",
            ]

            schema.add_column(cols[0], "TEXT")
            schema.add_column(cols[1], "TEXT")
            schema.add_column(cols[2], "TEXT")
            schema.add_column(cols[3], "TEXT")
            schema.add_column(cols[4], "INTEGER")

            unique_cols.extend(cols)

        schema.add_column(
            "call_stk",
            "TEXT",
        )

        schema.add_column(
            "call_depth",
            "INTEGER",
        )

        if unique_cols:
            schema.add_unique(unique_cols)

        return schema