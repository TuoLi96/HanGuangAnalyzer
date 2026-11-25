from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class FuncUseItem:
    src_file: str
    func_name: str
    use_file: str
    use_info: str
    use_type: str


class FuncUseMgr(TBLMgr):
    COLUMNS = [
        "src_file",
        "func_name",
        "use_file",
        "use_info",
        "use_type",
    ]
    
    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "func_use")
        self.func_use_items: list[FuncUseItem] = []

    def record(self, src_file: str, func_name: str,
                use_file: str, use_info: str, 
                use_type: str):
        return self.insert(
            {
                "src_file": src_file,
                "func_name": func_name,
                "use_file": use_file,
                "use_info": use_info,
                "use_type": use_type
            }
        )

    def _parse_row(self, row):
        return FuncUseItem(
            src_file=row.get("src_file", ""),
            func_name=row.get("func_name", ""),
            use_file=row.get("use_file", ""),
            use_info=row.get("use_info", ""),
            use_type=row.get("use_type", ""),
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.func_use_items = [self._parse_row(row) for row in rows]
        return self.func_use_items

    def get_by_func_name(self, func_name: str):
        rows = self.select(self.COLUMNS,
            {
                "func_name": func_name
            }
        )
        self.func_use_items = [self._parse_row(row) for row in rows]
        return self.func_use_items

    def get_by_src_func_name(self, src_file:str, func_name: str):
        rows = self.select(self.COLUMNS,
            {
                "src_file": src_file,
                "func_name": func_name
            }
        )
        self.func_use_items = [self._parse_row(row) for row in rows]
        return self.func_use_items