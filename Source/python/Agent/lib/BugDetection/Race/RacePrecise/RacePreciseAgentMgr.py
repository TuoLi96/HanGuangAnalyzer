from pathlib import Path
from HG.Knowledge.SymMgr import SymMgr
from HG.Agent.Base import AgentMgr
from HG.Agent.BugDetection.BugTool import BugToolMgr
from HG.Analyzer.Concurrency import ConcMgr
from HG.Analyzer.Concurrency.RaceDetector import RaceRoughMgr, RacePreciseMgr

class RacePreciseAgentMgr(AgentMgr):
    def __init__(self):
        super().__init__("RacePrecise")
        self.sym_mgr = SymMgr()
        bug_tool_mgr = BugToolMgr(self)
        bug_tool_mgr.register_bug_tools()
        conc_mgr = ConcMgr()
        self.race_rough_mgr = RaceRoughMgr(conc_mgr.get_race_db_mgr())
        self.race_precise_mgr = RacePreciseMgr(conc_mgr.get_race_db_mgr())
        self.register_self_tools()

    def get_agent_dir(self):
        return Path("BugDetection") / "Race" / "RacePrecise"

    def register_self_tools(self):
        self.register_agent_tool("dump_race_conclusion", self.dump_race_conclusion)
        self.label_finished_tool("dump_race_conclusion")

    def dump_race_conclusion(self, task_id, conclusion, summary):
        item = self.race_rough_mgr.get_by_id(task_id)
        is_true = int(conclusion)

        conclusion_file_path = self.agent_result_dir / (f"{conclusion}-{task_id}.md")
        bug_code = self.sym_mgr.get_func_def(item.src_file, item.func_name)
        write_code = self.sym_mgr.get_func_def(item.write_file, item.write_func)
        demo_code = self.sym_mgr.get_func_def(item.demo_file, item.demo_func)

        with open(conclusion_file_path, "w", encoding="utf-8") as f:
            content = (
                f"## Basic Information\n\n"
                f"### Bug information\n"
                f"- File: {item.src_file}\n"
                f"- Func: {item.func_name}\n"
                f"- Access Line: {item.access_line}\n"
                f"- Access Var: {item.access_var}\n"
                f"- Access Type: {item.access_type}\n"
                f"- Lock Var: {item.lock_var}\n\n"

                f"### Write operation\n"
                f"- Write File: {item.write_file}\n"
                f"- Write Func: {item.write_func}\n"
                f"- Write Line: {item.write_line}\n\n"

                f"### Demo\n"
                f"- Demo File: {item.demo_file}\n"
                f"- Demo Func: {item.demo_func}\n"
                f"- Demo Lock Line: {item.demo_lock_line}\n"
                f"- Demo Access Line: {item.demo_access_line}\n\n"

                f"## Detailed Analysis\n\n"
                f"### Summary\n"
                f"{summary}\n\n"

                f"## Related Code\n\n"

                f"### Race Code\n"
                f"```c\n"
                f"{bug_code}\n"
                f"```\n\n"

                f"### Demo Code\n"
                f"```c\n"
                f"{demo_code}\n"
                f"```\n\n"

                f"### Write Code\n"
                f"```c\n"
                f"{write_code}\n"
                f"```\n"
            )
            f.write(content)

        self.race_precise_mgr.record(
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
                item.demo_count,
                is_true,
                summary
        )
