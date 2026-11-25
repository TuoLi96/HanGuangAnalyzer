from .PathMgr import PathMgr


class DBPathMgr(PathMgr):

    def __init__(self):
        super().__init__()
        self.schema_root = (self.project_root / "DBSchema")
        self.db_dir = (self.work_root / "database")
        self.compile_db_path = (self.db_dir / "compile.db")
        self.knowledge_db_path = (self.db_dir / "knowledge.db")
        self.agent_db_path = (self.db_dir / "agent.db")


    def get_db_schema_root(self):
        return str(self.schema_root)

    def get_db_dir(self):
        return str(self.db_dir)

    def get_compile_db_path(self):
        return str(self.compile_db_path)

    def get_compile_db_lock_path(self):
        return str(self.db_dir / "compile_db.lock")

    def get_knowledge_db_path(self):
        return str(self.knowledge_db_path)

    def get_knowledge_db_lock_path(self):
        return str(self.db_dir / "knowledge_db.lock")

    def get_agent_db_path(self):
        return str(self.agent_db_path)

    def get_agent_db_lock_path(self):
        return str(self.db_dir / "agent_db.lock")