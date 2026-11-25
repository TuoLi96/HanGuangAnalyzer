from .PathMgr import PathMgr


class ConfigPathMgr(PathMgr):
    def __init__(self):
        super().__init__()
        self.config_dir = (self.work_root / "config")
        self.work_config_path = (self.config_dir / "work.config")
        self.compile_config_path = (self.config_dir / "compile.config")


    def get_work_config_path(self):
        return str(self.work_config_path)

    def get_compile_config_path(self):
        return str(self.compile_config_path)