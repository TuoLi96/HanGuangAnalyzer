import json

from HG.Common.Path import PathMgr
from HG.Agent.Base.Chat import DSChat
from HG.Agent.Base.Chat import GLMChat
from HG.Agent.Base.Chat import GPTChat
from HG.Agent.Base.Chat import QwenChat
from HG.Agent.Base.Chat import ParateraChat
from HG.Agent.Base.Chat import TinyChat

class ChaterMgr(PathMgr):
    def __init__(self):
        super().__init__()
        self.chater_config_path = self.config_root / "chat.config"

        with open(self.chater_config_path, "r", encoding="utf-8") as f:
            self.chater_config = json.load(f)

        self.chater_provider = self.chater_config["provider"]
        self.chater_model = self.chater_config["model"]

    def get_chater(self, chat_id, agent_mgr):
        if self.chater_provider == "DeepSeek":
            return DSChat(chat_id, agent_mgr, self.chater_model)
        elif self.chater_provider == "Qwen":
            return QwenChat(chat_id, agent_mgr, self.chater_model)
        elif self.chater_provider == "GLM":
            return GLMChat(chat_id, agent_mgr, self.chater_model)
        elif self.chater_provider == "GPT":
            return GPTChat(chat_id, agent_mgr, self.chater_model)
        elif self.chater_provider == "Paratera":
            return ParateraChat(chat_id, agent_mgr, self.chater_model)
        elif self.chater_provider == "Tiny":
            return TinyChat(chat_id, agent_mgr, self.chater_model)
        else:
            raise ValueError(f"Unknown chat provider: {self.chater_provider}")

    def get_in_cost(self):
        return self.chater_config[self.chater_provider][self.chater_model]["in_cost"]

    def get_cached_in_cost(self):
        return self.chater_config[self.chater_provider][self.chater_model]["cached_in_cost"]

    def get_out_cost(self):
        return self.chater_config[self.chater_provider][self.chater_model]["out_cost"]

    def get_tiny_chater(self, chat_id, agent_mgr):
        return TinyChat(chat_id, agent_mgr)