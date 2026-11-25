from pathlib import Path
import json
from tqdm import tqdm

from HG.Common.Path import PathMgr
from HG.Knowledge.SymMgr import SymMgr
from HG.Agent.Base.BasicTool import SearchToolMgr

class BugToolMgr(PathMgr):
    def __init__(self, agent_mgr):
        super().__init__()
        self.tool_json_root = self.project_root / "Metadata" / "Agent" / "Tools"

        self.agent_mgr = agent_mgr
        self.sym_mgr = SymMgr()
        self.search_tool_mgr = SearchToolMgr()

    def register_tool(self, tool_name, tool_dir, tool_func):
        tool_json = tool_dir / (f"{tool_name}.json")
        with open(tool_json, "r", encoding="utf-8") as f:
            tool_desp = json.load(f)
        self.agent_mgr.register_general_tool(tool_name, tool_func, tool_desp)

    def register_bug_tools(self):
        bug_tool_dir = self.tool_json_root / "BugDetection" / "BugTool"
        self.register_tool("get_func_def", bug_tool_dir, self.sym_mgr.get_func_def)
        self.register_tool("get_func_use", bug_tool_dir, self.sym_mgr.get_func_use)
        self.register_tool("get_macro_def", bug_tool_dir, self.sym_mgr.get_macro_def)
        self.register_tool("get_gvar_def", bug_tool_dir, self.sym_mgr.get_gvar_def)
        self.register_tool("get_struct_def", bug_tool_dir, self.sym_mgr.get_struct_def)
        self.register_tool("get_doc", bug_tool_dir, self.sym_mgr.get_doc)

    def register_basic_tools(self):
        basic_tool_dir = self.tool_json_root / "Basic" / "BasicTool"
        self.register_tool("search_text", basic_tool_dir, self.search_tool_mgr.search_text)
        self.register_tool("read_file", basic_tool_dir, self.search_tool_mgr.read_file)