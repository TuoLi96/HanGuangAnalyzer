from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class FuncDefItem:
    src_file: str
    func_name: str
    is_static: int
    is_inline: int
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int

class FuncDefMgr(TBLMgr):
    COLUMNS = [
        "src_file",
        "func_name",
        "is_static",
        "is_inline",
        "start_line",
        "end_line",
        "start_byte",
        "end_byte",
    ]
    
    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "func_def")
        self.func_def_items: list[FuncDefItem] = []

    def record(self, src_file: str, func_name: str,
                is_static: int, is_inline: int, 
                start_line: int, end_line: int,
                start_byte: int, end_byte: int):
        return self.insert(
            {
                "src_file": src_file,
                "func_name": func_name,
                "is_static": is_static,
                "is_inline": is_inline,
                "start_line": start_line,
                "end_line": end_line,
                "start_byte": start_byte,
                "end_byte": end_byte
            }
        )

    def _parse_row(self, row):
        return FuncDefItem(
            src_file=row.get("src_file", ""),
            func_name=row.get("func_name", ""),
            is_static=row.get("is_static", 0),
            is_inline=row.get("is_inline", 0),
            start_line=row.get("start_line", 0),
            end_line=row.get("end_line", 0),
            start_byte=row.get("start_byte", 0),
            end_byte=row.get("end_byte", 0),
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.func_def_items = [self._parse_row(row) for row in rows]
        return self.func_def_items

    def get_by_func_name(self, func_name: str):
        rows = self.select(self.COLUMNS,
            {
                "func_name": func_name
            }
        )
        self.func_def_items = [self._parse_row(row) for row in rows]
        return self.func_def_items