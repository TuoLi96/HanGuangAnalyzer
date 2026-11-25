from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class MacroDefItem:
    src_file: str
    macro_name: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int

class MacroDefMgr(TBLMgr):
    COLUMNS = [
        "src_file",
        "macro_name",
        "start_line",
        "end_line",
        "start_byte",
        "end_byte",
    ]
    
    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "macro_def")
        self.macro_def_items: list[MacroDefItem] = []

    def record(self, src_file: str, macro_name: str,
                start_line: int, end_line: int,
                start_byte: int, end_byte: int):
        return self.insert(
            {
                "src_file": src_file,
                "macro_name": macro_name,
                "start_line": start_line,
                "end_line": end_line,
                "start_byte": start_byte,
                "end_byte": end_byte
            }
        )

    def _parse_row(self, row):
        return MacroDefItem(
            src_file=row.get("src_file", ""),
            macro_name=row.get("macro_name", ""),
            start_line=row.get("start_line", 0),
            end_line=row.get("end_line", 0),
            start_byte=row.get("start_byte", 0),
            end_byte=row.get("end_byte", 0),
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.macro_def_items = [self._parse_row(row) for row in rows]
        return self.macro_def_items

    def get_by_macro_name(self, macro_name: str):
        rows = self.select(self.COLUMNS,
            {
                "macro_name": macro_name
            }
        )
        self.macro_def_items = [self._parse_row(row) for row in rows]
        return self.macro_def_items