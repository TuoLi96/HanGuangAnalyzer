import os
from pathlib import Path

class PathMgr:
    def __init__(self):
        self.project_root = Path(os.environ.get("HG_ROOT", ""))
        self.config_root = self.project_root / "Config"
        self.metadata_root = self.project_root / "Metadata"

        self.project_bin_root = self.project_root / "install" / "bin"
        self.project_include_root = self.project_root / "install" / "include"
        self.project_lib_root = self.project_root / "install" / "lib"

        self.work_root = Path(os.environ.get("HG_WORK_ROOT", ""))
        self.db_root =  self.work_root / "database"
        self.checked_src_root = Path(os.environ.get("HG_CHECKED_SRC", ""))

        self.linux_git = self.work_root / "linux-git"

    def get_project_root(self):
        return str(self.project_root)

    def get_config_root(self):
        return str(self.config_root)

    def get_metadata_root(self):
        return str(self.metadata_root)

    def get_project_bin_root(self):
        return str(self.project_bin_root)

    def get_project_include_root(self):
        return str(self.project_include_root)

    def get_project_lib_root(self):
        return str(self.project_lib_root)

    def get_work_root(self):
        return str(self.work_root)

    def get_db_root(self):
        return str(self.db_root)

    def get_checked_root(self):
        return str(self.checked_src_root)

    def get_linux_git_path(self):
        return str(self.linux_git)

    def get_repath_to_src(self, path_str: str):
        src_path = Path(path_str)
        src_path = Path(os.path.normpath(src_path))
        if not src_path.is_absolute():
            return str(src_path)
        try:
            re_src_path = src_path.relative_to(self.checked_src_root)
            return str(re_src_path)
        except ValueError:
            return ""

    def get_abspath_from_src(self, path_str: str):
        src_path = Path(path_str)
        src_path = Path(os.path.normpath(src_path))
        if src_path.is_absolute():
            return str(src_path)
        abs_src_path = self.checked_src_root / src_path
        return str(abs_src_path)