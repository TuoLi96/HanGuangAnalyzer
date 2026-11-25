from openai import OpenAI
import os
import json
from tqdm import tqdm

from HG.Agent.Base.Chat import ChatSession

class ParateraChat(ChatSession):
    def __init__(self, chat_id, agent_mgr, model):
        super().__init__(chat_id, agent_mgr)
        self.client = OpenAI(
            base_url="https://llmapi.paratera.com",
            api_key=os.environ.get("PARATERA_API_KEY")
        )
        self.model = model

    def chat(self, message):
        self.add_user(message)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.whole_messages,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
                temperature=0.7,
                top_p=0.9
            )
            usage = resp.usage
            in_tok = usage.prompt_tokens
            out_tok = usage.completion_tokens
            total_tok = usage.total_tokens
            cached_tok = 0
            if usage.prompt_tokens_details:
                cached_tok = usage.prompt_tokens_details.cached_tokens
            msg = resp.choices[0].message
            self.add_assistant(
                msg.content or "",
                getattr(msg, "reasoning_content",  None),
                msg.tool_calls,
                in_tok,
                out_tok,
                total_tok,
                cached_tok
            )
            return msg.content or ""
        except Exception as e:
            tqdm.write(f"[{self.chat_id}] chat failed: {type(e).__name__}: {e}")
            return ""

    def chat_with_tools(self, max_rounds):
        try:
            _round = 0
            while _round < max_rounds:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.whole_messages,
                    stream=False,
                    extra_body={"thinking": {"type": "disabled"}},
                    tools=self.tool_list,
                    temperature=0.7,
                    top_p=0.9
                )
                usage = resp.usage
                in_tok = usage.prompt_tokens
                out_tok = usage.completion_tokens
                total_tok = usage.total_tokens
                cached_tok = 0
                if usage.prompt_tokens_details:
                    cached_tok = usage.prompt_tokens_details.cached_tokens
                msg = resp.choices[0].message
                self.add_assistant(
                    msg.content or "",
                    getattr(msg, "reasoning_content",  None),
                    msg.tool_calls,
                    in_tok,
                    out_tok,
                    total_tok,
                    cached_tok
                )
                if msg.tool_calls:
                    is_finish = False
                    for tool_call in msg.tool_calls:
                        tool_name = "unknown"
                        tool_call_id = tool_call.id
                        try:
                            tool_name = tool_call.function.name
                            raw_arguments = tool_call.function.arguments
                            arguments = json.loads(raw_arguments)
                            tool_ret = self.call_tool(tool_name, arguments)
                            if self.agent_mgr.is_finish(tool_name):
                                is_finish = True
                            _round += 1
                        except Exception as e:
                            tool_ret = {
                                "error": True,
                                "message": str(e),
                                "tool": tool_name,
                                "instruction": "Please fix the tool call and try again."
                            }
                            tqdm.write(tool_ret)
                        tool_ret = json.dumps(tool_ret, ensure_ascii=False)
                        self.add_tool(tool_ret, tool_call_id)
                    if is_finish:
                        return True
                else:
                    self.add_runtime_user("You need use tools to verify the analysis or output the result!")
            if _round == max_rounds:
                tqdm.write(f"Out of the max rounds: {_round}")
            return False
        except Exception as e:
            tqdm.write(f"[{self.chat_id}] chat (with tools) failed: {type(e).__name__}: {e}")
            return False
