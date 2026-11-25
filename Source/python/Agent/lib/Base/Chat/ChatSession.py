import threading
import json
import os

chat_record_lock = threading.Lock()

class ChatSession:
    token_lock = threading.Lock()
    token_usage = {}
    token_loaded = set()

    def __init__(self, chat_id, agent_mgr):
        self.chat_id = chat_id
        self.agent_mgr = agent_mgr
        self.system_prompt = self.agent_mgr.get_system_prompt()

        self.whole_messages = [{"role": "system", "content": self.system_prompt}]
        self.chat_rnd = 0
        self.chat_mgr = self.agent_mgr.get_chat_mgr()

        self.tool_list = list(self.agent_mgr.get_tool_list())
        self.tool_api = dict(self.agent_mgr.get_tool_api())

        self.token_file = self.agent_mgr.get_token_path()
        self.load_token_usage()

        self.record("system", self.system_prompt)

    def record(self, role, message, tool_id=None, 
            thinking_text=None, tool_calls=None,
            in_tok=0, out_tok=0, total_tok=0, cached_tok=0
        ):
        tool_id = tool_id or ""
        thinking_text = thinking_text or ""
        if tool_calls is None:
            tool_calls = ""
        else:
            tool_calls = json.dumps(
                [
                    tcall.model_dump()
                    if hasattr(tcall, "model_dump")
                    else tcall
                    for tcall in tool_calls
                ],
                ensure_ascii=False
            )
        with chat_record_lock:
            self.chat_mgr.record(self.chat_id, self.chat_rnd, role, 
                message, tool_id, thinking_text, tool_calls,
                in_tok, out_tok, total_tok, cached_tok
            )
            self.chat_rnd += 1

    def add_runtime_system(self, message):
        self.whole_messages.append({"role": "system", "content": message})

    def add_assistant(self, message, thinking_text=None, tool_calls=None, 
            in_tok=0, out_tok=0, total_tok=0, cached_tok=0
        ):
        item = {
            "role": "assistant",
            "content": message
        }
        if thinking_text:
            item["reasoning_content"] = thinking_text
        if tool_calls is not None:
            item["tool_calls"] = [
                tcall.model_dump()
                if hasattr(tcall, "model_dump")
                else tcall
                for tcall in tool_calls
            ]
        self.whole_messages.append(item)
        self.record("assistant", message, None, thinking_text, tool_calls,
            in_tok, out_tok, total_tok, cached_tok
        )
        if total_tok > 0:
            self.add_token_usage(in_tok, out_tok, total_tok, cached_tok)

    def add_tool(self, message, tool_id):
        item = {
            "role": "tool",
            "tool_call_id": tool_id,
            "content": message
        }
        self.whole_messages.append(item)
        self.record("tool", message, tool_id, None, None)

    def add_user(self, message):
        self.whole_messages.append({"role": "user", "content": message})
        self.record("user", message, None, None, None)

    def add_runtime_user(self, message):
        self.whole_messages.append({"role": "user", "content": message})
        
    def prepare(self, task, context):
        self.add_user(task)
        self.add_assistant(context)

    def prepare_with_thinking(self, task, context):
        self.add_user(task)
        self.add_assistant("I will continue to analyze.", context)
            
    def call_tool(self, name, arguments):
        if name not in self.tool_api:
            return {
                "success": False,
                "error": f"Unknown tool {name}"
            }
        try:
            result = self.tool_api[name](**arguments)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def load_token_usage(self):
        with ChatSession.token_lock:
            if self.token_file in ChatSession.token_loaded:
                return
            ChatSession.token_usage[self.token_file] = {
                "in_tok": 0,
                "out_tok": 0,
                "total_tok": 0,
                "cached_tok": 0
            }
            if os.path.exists(self.token_file):
                with open(self.token_file) as f:
                    ChatSession.token_usage[self.token_file] = json.load(f)
            ChatSession.token_loaded.add(self.token_file)

    def add_token_usage(self, in_tok, out_tok, total_tok, cached_tok):
        with ChatSession.token_lock:
            usage = ChatSession.token_usage[self.token_file]

            usage["in_tok"] += in_tok
            usage["out_tok"] += out_tok
            usage["total_tok"] += total_tok
            usage["cached_tok"] += cached_tok

    def save_token_usage(self):
        with ChatSession.token_lock:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            tmp = self.token_file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(ChatSession.token_usage[self.token_file], f, indent=4)
            os.replace(tmp, self.token_file)

    def get_token_usage(self, in_cost, cached_in_cost, out_cost):
        with ChatSession.token_lock:
            usage = ChatSession.token_usage[self.token_file]
            uncached_in_tok = usage["in_tok"] - usage["cached_tok"]
            cache_hit_rate = (usage["cached_tok"] / usage["in_tok"] if usage["in_tok"] > 0 else 0)
            cost = (uncached_in_tok / 1e6 * in_cost +
                    usage['cached_tok'] / 1e6 * cached_in_cost +
                    usage['out_tok'] / 1e6 * out_cost)
            return (
                f"Token Usage: "
                f"in={usage['in_tok']/1e6:.2f}M, "
                f"cached={usage['cached_tok']/1e6:.2f}M ({cache_hit_rate:.2%}), "
                f"out={usage['out_tok']/1e6:.2f}M, "
                f"total={usage['total_tok']/1e6:.2f}M, "
                f"cost={cost:.2f}"
            )
