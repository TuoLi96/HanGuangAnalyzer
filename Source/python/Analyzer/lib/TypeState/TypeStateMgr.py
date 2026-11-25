from pathlib import Path
import json
from HG.Common.Path import PathMgr
from HG.Common.Database import DBMgr

class TypeStateMgr(PathMgr):
    def __init__(self):
        super().__init__()
        self.ts_dir = self.metadata_root / "Analyzer" / "BugDetection" / "TSes"
        self.ts_dict_path = self.ts_dir / "ts.json"
        with open(self.ts_dict_path, "r", encoding="utf-8") as f:
            self.ts_dict = json.load(f)
        
        ts_db_path = self.db_root / "Bug" / "typestate.db"
        ts_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ts_db_mgr = DBMgr(str(ts_db_path))

    def get_ts_db_mgr(self):
        return self.ts_db_mgr

    def get_ts_dict(self):
        return self.ts_dict

    def get_ts_path(self, checker):
        checker_json = f"{checker}.json"
        checker_path = self.ts_dir / checker_json
        return str(checker_path)