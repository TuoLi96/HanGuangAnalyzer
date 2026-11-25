from dataclasses import dataclass

from HG.Common.Database import TBLMgr
from HG.Common.Database import DBMgr

@dataclass
class ChatItem:
    chat_id: int
    chat_rnd: int
    role: str
    content: str
    tool_id: int
    thinking_text: str
    tool_calls: str
    in_tok: int
    out_tok: int
    total_tok: int
    cached_tok: int

class ChatMgr(TBLMgr):
    COLUMNS = [
        "chat_id",
        "chat_rnd",
        "role",
        "content",
        "tool_id",
        "thinking_text",
        "tool_calls",
        "in_tok",
        "out_tok",
        "total_tok",
        "cached_tok"
    ]
    
    def __init__(self, db_mgr: DBMgr):
        super().__init__(db_mgr, "chat")
        self.chat_items: list[ChatMgr] = []

    def record(self, chat_id: int, chat_rnd: int, role: str, content: str, 
                tool_id: str, thinking_text: str, tool_calls: str, 
                in_tok: int, out_tok: int, total_tok: int, cached_tok: int):
        return self.insert(
            {
                "chat_id": chat_id,
                "chat_rnd": chat_rnd,
                "role": role,
                "content": content,
                "tool_id": tool_id,
                "thinking_text": thinking_text,
                "tool_calls": tool_calls,
                "in_tok": in_tok,
                "out_tok": out_tok,
                "total_tok": total_tok,
                "cached_tok": cached_tok,
            }
        )

    def _parse_row(self, row):
        return ChatItem(
            chat_id=row.get("chat_id", 0),
            chat_rnd=row.get("chat_rnd", 0),
            role=row.get("role", ""),
            content=row.get("content", ""),
            tool_id=row.get("tool_id", ""),
            thinking_text=row.get("thinking_text", ""),
            tool_calls=row.get("tool_calls", ""),
            in_tok=row.get("in_tok", 0),
            out_tok=row.get("out_tok", 0),
            total_tok=row.get("total_tok", 0),
            cached_tok=row.get("cached_tok", 0)
        )

    def get_all(self):
        rows = self.select(self.COLUMNS)
        self.chat_items = [self._parse_row(row) for row in rows]
        return self.chat_items

    def get_by_chat_id(self, chat_id: int):
        rows = self.select(self.COLUMNS,
            {
                "chat_id": chat_id
            }
        )
        self.chat_items = [self._parse_row(row) for row in rows]
        return self.chat_items

    def get_by_tool_id(self, tool_id):
        rows = self.select(self.COLUMNS,
            {
                "tool_id": tool_id
            }
        )
        self.chat_items = [self._parse_row(row) for row in rows]
        return self.chat_items