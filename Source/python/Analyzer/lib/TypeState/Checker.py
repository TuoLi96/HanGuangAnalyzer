from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from HG.Common.Database.DBMgr import DBMgr
from HG.Common.Database.DynamicTBLMgr import DynamicTBLMgr

@dataclass
class KeyActionInfo:
    action: str
    desp: str

@dataclass
class BugInfo:
    bug_name: str = ""
    tbl_name: str = ""
    bug_desp: str = ""
    key_actions: list[KeyActionInfo] = field(default_factory=list)
    bug_state: str = ""

class Checker:
    def __init__(self, ts_json_path: str | Path, ts_db_mgr: DBMgr) -> None:
        self.ts_db_mgr = ts_db_mgr
        self.bug_info = BugInfo()
        
        with open(ts_json_path, "r", encoding="utf-8") as f:
            ts_json = json.load(f)
        self.collect_bug_info(ts_json)
        self.tbl_mgr = DynamicTBLMgr(ts_db_mgr, self.bug_info.tbl_name)

    def collect_bug_info(self, ts_json: dict[str, Any]) -> None:
        bug = ts_json.get("bug", {})

        self.bug_info = BugInfo(
            bug_name=bug.get("name", ""),
            tbl_name=bug.get("tbl", ""),
            bug_desp=bug.get("bug_desp", ""),
            key_actions=[
                KeyActionInfo(
                    action=item.get("action", ""),
                    desp=item.get("act_desp", ""),
                ) for item in bug.get("key_actions", [])
            ],
            bug_state=bug.get("bug_state", ""),
        )

    def select(self,
        columns: list[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self.tbl_mgr.select(
            columns=columns,
            where=where,
        )

    def get_all_bug_desp(self) -> list[str]:
        bug_list = self.select()
        bug_desp_list = []

        for bug in bug_list:
            bug_desp = (
                f"Here is a possible {bug['name']}. "
                f"{self.bug_info.bug_desp}\n"
            )
            for key_action in self.bug_info.key_actions:
                act_col = f"{key_action.action}_name"
                file_col = f"{key_action.action}_src_file"
                func_col = f"{key_action.action}_func_name"
                var_col = f"{key_action.action}_var_name"
                line_col = f"{key_action.action}_line"

                act_name = bug[act_col]
                file_name = bug[file_col]
                func_name = bug[func_col]
                var_name = bug[var_col]
                line = bug[line_col]

                if (act_name == "" or
                        file_name == "" or
                        func_name == "" or
                        line <= 0):
                    bug_desp = ""
                    break
                if "[OBJ]" in key_action.desp and not var_name:
                    bug_desp = ""
                    break

                act_desp = key_action.desp.replace("[OBJ]", var_name)

                bug_desp += (
                    f"{act_desp} at {file_name}:{line} "
                    f"in function {func_name}.\n"
                )

            if bug_desp:
                if bug["call_stk"]:
                    if "-1" in bug["call_stk"]:
                        continue
                    bug_desp += (f"{bug["call_stk"]}\n")
                bug_desp_list.append(bug_desp)
            

        return bug_desp_list