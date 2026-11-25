
from HG.Analyzer.TypeState import TypeStateMgr, Checker
from HG.Agent.BugDetection.TypeState import TSAgentMgr
import json

def main():
    ts_agent_mgr = TSAgentMgr()
    task_path = ts_agent_mgr.get_task_path()
    with open(task_path, "w", encoding="utf-8") as f:
        ts_mgr = TypeStateMgr()
        ts_dict = ts_mgr.get_ts_dict()
        task_id = 1
        for ts_name, settings in ts_dict.items():
            if settings.get("enable", False):
                checker = Checker(ts_mgr.get_ts_path(ts_name), ts_mgr.get_ts_db_mgr())
                bug_list = checker.get_all_bug_desp()
                for bug in bug_list:
                    bug_info = {
                        "type" : ts_name,
                        "desp" : f"ID-{task_id}. {bug}"
                    }
                    f.write(json.dumps(bug_info, ensure_ascii=False) + "\n")
                    task_id = task_id + 1

if __name__ == "__main__":
    main()
