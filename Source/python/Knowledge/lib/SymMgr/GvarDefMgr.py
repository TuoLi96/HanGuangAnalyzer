from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class GvarDefItem:
    src_file: str
    gvar_name: str
    gvar_type: str
    is_static: int
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int

class GvarDefMgr(TBLMgr):
    COLUMNS = [
        "src_file",
        "gvar_name",
        "gvar_type",
        "is_static",
        "start_line",
        "end_line",
        "start_byte",
        "end_byte",
    ]
    
    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "gvar_def")
        self.gvar_def_items: list[GvarDefItem] = []

    def record(self, src_file: str, gvar_name: str, gvar_type: str,
                is_static: int, start_line: int, end_line: int,
                start_byte: int, end_byte: int):
        return self.insert(
            {
                "src_file": src_file,
                "gvar_name": gvar_name,
                "gvar_type": gvar_type,
                "is_static": is_static,
                "start_line": start_line,
                "end_line": end_line,
                "start_byte": start_byte,
                "end_byte": end_byte
            }
        )

    def _parse_row(self, row):
        return GvarDefItem(
            src_file=row.get("src_file", ""),
            gvar_name=row.get("gvar_name", ""),
            gvar_type=row.get("gvar_type", ""),
            is_static=row.get("is_static", 0),
            start_line=row.get("start_line", 0),
            end_line=row.get("end_line", 0),
            start_byte=row.get("start_byte", 0),
            end_byte=row.get("end_byte", 0),
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.gvar_def_items = [self._parse_row(row) for row in rows]
        return self.gvar_def_items

    def get_by_gvar_name(self, gvar_name: str):
        rows = self.select(self.COLUMNS,
            {
                "gvar_name": gvar_name
            }
        )
        self.gvar_def_items = [self._parse_row(row) for row in rows]
        return self.gvar_def_items