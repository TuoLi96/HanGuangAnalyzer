import json
from pathlib import Path

from .PathMgr import PathMgr


class WorkPathMgr(PathMgr):

    def __init__(self, config_path_mgr):
        super().__init__()
        work_config_path = (config_path_mgr.get_work_config_path())
        with open(work_config_path, "r") as f:
            self.work_config = json.load(f)

        self.src_root = Path(self.work_config["src_root"])
        self.compile_root = (self.work_root / "compile")
        self.ir_dir = (self.compile_root / "IRs")
        self.log_root = (self.work_root / "Logs")
        self.data_root = (self.work_root / "Data")

    def get_src_root(self):
        return str(self.src_root)

    def get_compile_root(self):
        return str(self.compile_root)

    def get_ir_dir(self):
        return str(self.ir_dir)

    def get_log_root(self):
        return str(self.log_root)

    def get_data_root(self):
        return str(self.data_root)

    def get_ms_swift_data_path(self):
        return str(self.data_root / "ms_swift_data.jsonl")