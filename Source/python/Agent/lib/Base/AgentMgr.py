from HG.Common.Path import PathMgr
from HG.Common.Database import DBMgr
from HG.Agent.Base.Chat import ChatMgr

from abc import ABC, abstractmethod
import json
import threading
import os

checkpoint_lock = threading.Lock()

class AgentMgr(PathMgr, ABC):
    def __init__(self, agent_name):
        super().__init__()
        self.agent_name = agent_name
        self.db_schema_root = self.project_root / "Metadata" / "Agent" / "DBSchema"
        self.prompt_root = self.project_root / "Metadata" / "Agent" / "Prompt"
        self.tool_json_root = self.project_root / "Metadata" / "Agent" / "Tools"

        self.agent_work_dir = self.work_root / "AgentTasks" / self.agent_name
        self.task_path = self.agent_work_dir / "tasks.jsonl"
        self.agent_result_dir = self.agent_work_dir / "Result"
        self.agent_checkpoint_path = self.agent_result_dir / "checkpoint.json"
        self.agent_token_path = self.agent_result_dir / "token.json"
        self.agent_db_path = self.work_root / "database" / "Agent" / (f"{self.agent_name}.db")
        self.finished = set()
        
        self.chat_mgr : ChatMgr
        self.system_prompt : str
        self.task_prompt : str
        self.tasks = []
        self.tool_black_list = []
        self.tool_list = []
        self.tool_api = {}
        self.finish_tool_list = []

        self.prepare_work_dir()
        self.prepare_db()
        self.load_prompts()
        self.load_tasks()
        self.load_checkpoint()
        self.load_tool_black_list()

        self.checkpoint_cnt = 0

        self.agent_config_path = self.config_root / "agent.config"
        with open(self.agent_config_path, "r", encoding="utf-8") as f:
            self.agent_config = json.load(f)
        self.num_threads = self.agent_config["threads"]
        self.max_tool_rounds = self.agent_config["max_tool_rounds"]
        self.batch_size = self.agent_config["batch_size"]

    @abstractmethod
    def get_agent_dir(self):
        pass

    def prepare_db(self):
        db_schema_path = self.db_schema_root / "Chat.schema"
        agent_db_mgr = DBMgr(self.agent_db_path)
        with open(db_schema_path, "r", encoding="utf-8") as f:
            db_schema = f.read()
            agent_db_mgr.execute(db_schema)
        self.chat_mgr = ChatMgr(agent_db_mgr)

    def prepare_work_dir(self):
        self.agent_work_dir.mkdir(parents=True, exist_ok=True)
        self.agent_result_dir.mkdir(parents=True, exist_ok=True)
        if not self.task_path.exists():
            self.task_path.touch()
        self.agent_db_path.parent.mkdir(parents=True, exist_ok=True)

    def load_prompts(self):
        prompt_dir = self.prompt_root / self.get_agent_dir()
        system_prompt_path = prompt_dir / "system.prompt"
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        task_prompt_path = prompt_dir / "task.prompt"
        with open(task_prompt_path, "r", encoding="utf-8") as f:
            self.task_prompt = f.read()
        
    def load_tasks(self):
        with open(self.task_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.tasks.append(
                    json.loads(line)
                )

    def load_checkpoint(self):
        if self.agent_checkpoint_path.exists():
            with open(self.agent_checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.finished = set(data.get("finished", []))

    def load_tool_black_list(self):
        enabled_tool_file = self.tool_json_root / "enabled_tools.json"
        with enabled_tool_file.open("r", encoding="utf-8") as f:
            tool_list = json.load(f)
        self.tool_black_list = [name for name, config in tool_list.items() if config.get("enable") is False]

    def save_checkpoint(self):
        tmp_path = self.agent_checkpoint_path.with_name(
            self.agent_checkpoint_path.name + ".tmp"
        )

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "finished": list(self.finished)
                },
                f
            )
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, self.agent_checkpoint_path)

    def get_token_path(self):
        return str(self.agent_token_path)

    def register_agent_tool(self, tool_name, tool_func):
        if tool_name in self.tool_api:
            raise RuntimeError(f"Tool already exists: {tool_name}")
        if tool_name in self.tool_black_list:
            return
        tool_desp_path = self.tool_json_root / self.get_agent_dir() / (f"{tool_name}.json")
        with open(tool_desp_path, "r", encoding="utf-8") as f:
             tool_desp = json.load(f)
        self.tool_list.append(tool_desp)
        self.tool_api[tool_name] = tool_func

    def register_general_tool(self, tool_name, tool_func, tool_desp):
        if tool_name in self.tool_api:
            raise RuntimeError(f"Tool already exists: {tool_name}")
        if tool_name in self.tool_black_list:
            return
        self.tool_list.append(tool_desp)
        self.tool_api[tool_name] = tool_func

    def label_finished_tool(self, tool_name):
        self.finish_tool_list.append(tool_name)

    def get_agent_lib_root(self):
        return self.agent_lib_root

    def get_chat_mgr(self):
        return self.chat_mgr
    
    def get_system_prompt(self):
        return self.system_prompt

    def get_task_prompt(self):
        return self.task_prompt

    def get_task_path(self):
        return str(self.task_path)

    def get_tasks(self):
        return self.tasks

    def get_tool_list(self):
        return self.tool_list

    def get_tool_api(self):
        return self.tool_api

    def done(self, idx):
        with checkpoint_lock:
            self.finished.add(idx)
            self.checkpoint_cnt += 1
            if self.checkpoint_cnt % 5 == 0:
                self.save_checkpoint()

    def is_done(self, idx):
        with checkpoint_lock:
            return idx in self.finished

    def is_finish(self, tool_name):
        return tool_name in self.finish_tool_list

    def get_num_threads(self):
        return self.num_threads

    def get_max_tool_rounds(self):
        return self.max_tool_rounds

    def get_batch_size(self):
        return self.batch_size