from openai import OpenAI
import os
import json
from tqdm import tqdm
from openai.types.chat import ChatCompletion

from HG.Agent.Base.Chat import ChatSession

class GPTChat(ChatSession):
    def __init__(self, chat_id, agent_mgr, model):
        super().__init__(chat_id, agent_mgr)
        self.client = OpenAI(
            base_url="https://ryugroup.uk/api/v1",
            api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN")
        )
        self.model = model

    def merge_stream_response(self, stream):
        content = ""
        tool_calls = {}

        response_id = None
        created = None
        model = None
        finish_reason = None
        system_fingerprint = None
        usage = None

        for chunk in stream:
            response_id = chunk.id
            created = chunk.created
            model = chunk.model

            if chunk.system_fingerprint:
                system_fingerprint = chunk.system_fingerprint

            if getattr(chunk, "usage", None) is not None:
                usage = chunk.usage

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                content += delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index

                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }

                    item = tool_calls[idx]

                    if tc.id:
                        item["id"] = tc.id

                    if tc.type:
                        item["type"] = tc.type

                    if tc.function:
                        if tc.function.name:
                            item["function"]["name"] += tc.function.name

                        if tc.function.arguments:
                            item["function"]["arguments"] += tc.function.arguments

            if choice.finish_reason:
                finish_reason = choice.finish_reason

        if response_id is None:
            raise ValueError("Empty stream response")

        message = {
            "role": "assistant",
            "content": content if content else None
        }

        if tool_calls:
            message["tool_calls"] = [
                tool_calls[i] for i in sorted(tool_calls)
            ]

        result = {
            "id": response_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
                "logprobs": None
            }]
        }

        if system_fingerprint:
            result["system_fingerprint"] = system_fingerprint

        if usage:
            result["usage"] = usage.model_dump()

        return ChatCompletion.model_validate(result)

    def chat(self, message):
        self.add_user(message)
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.whole_messages,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}},
                temperature=0.7,
                top_p=0.9
            )
            resp = self.merge_stream_response(stream)
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
            return None

    def chat_with_tools(self, max_rounds):
        try:
            _round = 0
            while _round < max_rounds:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.whole_messages,
                    stream=True,
                    extra_body={"thinking": {"type": "disabled"}},
                    tools=self.tool_list,
                    temperature=0.7,
                    top_p=0.9
                )
                resp = self.merge_stream_response(stream)
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
            if _round >= max_rounds:
                tqdm.write(f"Out of the max rounds: {_round}")
            return False
        except Exception as e:
            tqdm.write(f"[{self.chat_id}] chat (with tools) failed: {type(e).__name__}: {e}")
            return False
