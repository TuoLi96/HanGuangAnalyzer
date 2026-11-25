from pathlib import Path
from HG.Agent.Base import AgentMgr
from HG.Agent.BugDetection.BugTool import BugToolMgr

class TSAgentMgr(AgentMgr):
    def __init__(self):
        super().__init__("TypeState")
        bug_tool_mgr = BugToolMgr(self)
        bug_tool_mgr.register_bug_tools()
        bug_tool_mgr.register_basic_tools()
        self.register_self_tools()

    def get_agent_dir(self):
        return Path("BugDetection") / "TypeState"

    def register_self_tools(self):
        self.register_agent_tool("dump_ts_summary", self.dump_ts_summary)
        self.label_finished_tool("dump_ts_summary")

    def dump_ts_summary(self, task_id, conclusion, summary):
        summary_file_path = self.agent_result_dir / f"{task_id}_{conclusion}.md"
        with open(summary_file_path, "w", encoding="utf-8") as f:
            f.write(summary)
