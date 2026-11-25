from HG.Common.Path import PathMgr
from HG.Common.Database import DBMgr
from HG.Frontend import IncludeMgr, LinkMgr
import os
from pathlib import Path

class FrontendMgr(PathMgr):
    def __init__(self):
        super().__init__()
        self.compile_dir = self.work_root / "Compile"
        self.ir_dir = self.compile_dir / "IRs"
        self.ir_dir.mkdir(parents=True, exist_ok=True)
        self.compile_db_path = self.db_root / "Compile" / "compile.db"
        self.compile_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.compile_db_lock_path = self.db_root / "Compile" / "compile_db.lock"
        self.compile_db_mgr = DBMgr(str(self.compile_db_path))

        self.include_mgr = IncludeMgr(self.compile_db_mgr)
        self.link_mgr = LinkMgr(self.compile_db_mgr)

    def get_compile_db_mgr(self):
        return self.compile_db_mgr

    def get_include_mgr(self):
        return self.include_mgr

    def get_link_mgr(self):
        return self.link_mgr

    def get_compile_ir_dir(self):
        return str(self.ir_dir)

    def get_repath_of_ir(self, ir_path_str: str):
        ir_path = Path(ir_path_str)
        ir_path = Path(os.path.normpath(ir_path))
        if not ir_path.is_absolute():
            return str(ir_path)
        try:
            re_ir_path = ir_path.relative_to(self.ir_dir)
            return str(re_ir_path)
        except ValueError:
            return ""

    def get_abspath_of_ir(ir_path_str: str):
        ir_path = Path(ir_path_str)
        ir_path = Path(os.path.normpath(ir_path))
        if ir_path.is_absolute():
            return str(ir_path)
        abs_ir_path = self.ir_dir / ir_path
        return str(abs_ir_path)
