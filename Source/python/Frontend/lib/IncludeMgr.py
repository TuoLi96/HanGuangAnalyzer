from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class IncludeItem:
    main_file: str
    include_files: str

class IncludeMgr(TBLMgr):
    COLUMNS = [
        "main_file",
        "include_files",
    ]

    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "include")
        self.include_items = []

    def record(self, main_file: str,  include_files: str):
        return self.insert(
            {
                "main_file": main_file,
                "include_files": include_files,
            }
        )
        
    def _parse_row(self, row):
        return IncludeItem(
            main_file=row.get("main_file", ""),
            include_files=row.get("include_files", ""),
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.include_items = [self._parse_row(row) for row in rows]
        return self.include_items

    def get_by_main_file(self, main_file: str):
        rows = self.select(self.COLUMNS,
            {
                "main_file": main_file
            }
        )
        self.include_items = [self._parse_row(row) for row in rows]
        return self.include_items
