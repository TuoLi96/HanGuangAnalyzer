from pathlib import Path
from HG.Agent.Base import AgentMgr
from HG.Analyzer.Concurrency import ConcMgr
from HG.Analyzer.Concurrency.RaceDetector import AccessEventMgr, RaceRoughMgr

class RaceRoughAgentMgr(AgentMgr):
    def __init__(self):
        super().__init__("RaceRough")
        conc_mgr = ConcMgr()
        self.access_event_mgr = AccessEventMgr(conc_mgr.get_race_db_mgr())
        self.race_rough_mgr = RaceRoughMgr(conc_mgr.get_race_db_mgr())
        self.register_self_tools()

    def get_agent_dir(self):
        return Path("BugDetection") / "Race" / "RaceRough"

    def register_self_tools(self):
        self.register_agent_tool("record_kept_candidates", self.record_kept_candidates)
        self.label_finished_tool("record_kept_candidates")

    def record_kept_candidates(self, kept_ids: list[int]):
        for event_id in kept_ids:
            item = self.access_event_mgr.get_by_id(event_id)
            if item is None:
                continue
            self.race_rough_mgr.record(
                item.target_file,
                item.src_file,
                item.func_name,
                item.lock_var,
                item.access_var,
                item.access_line,
                item.access_type,
                item.is_write,
                item.has_protection,
                item.is_protected,
                item.write_file,
                item.write_func,
                item.write_line,
                item.demo_file,
                item.demo_func,
                item.demo_lock_line,
                item.demo_access_line,
                item.demo_count
            )
