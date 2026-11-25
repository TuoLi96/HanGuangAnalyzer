from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class LinkItem:
    target_file: str
    link_list: str
    ir_list: str

class LinkMgr(TBLMgr):
    COLUMNS = [
        "target_file",
        "link_list",
        "ir_list",
    ]
    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "link")
        self.link_items = []


    def record(self, target_file: str, link_list: str, ir_list: str):
        self.insert(
            {
                "target_file": target_file,
                "link_list": link_list,
                "ir_list": ir_list,
            }
        )
        
    def _parse_row(self, row):
        return LinkItem(
            target_file=row.get("target_file", ""),
            link_list=row.get("link_list", ""),
            ir_list=row.get("ir_list", ""),
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.link_items = [self._parse_row(row) for row in rows]
        return self.link_items

    def get_by_target_file(self,  target_file: str):
        rows = self.select(self.COLUMNS,
            {
                "target_file": target_file
            }
        )
        self.link_items = [self._parse_row(row) for row in rows]
        return self.link_items