from __future__ import annotations

import re

from .models import ParsedCommand


HELP_TEXT = "请按格式输入：查询 精灵名，或：配种 精灵名"


class CommandParser:
    def __init__(self, bot_name: str = "友哈巴赫") -> None:
        self.bot_name = bot_name
        self._mention_pattern = re.compile(rf"^\s*@{re.escape(bot_name)}(?:\s+|$)(.*)$", re.IGNORECASE)

    def parse(self, message: str) -> ParsedCommand:
        text = (message or "").strip()
        match = self._mention_pattern.match(text)
        if match:
            tail = match.group(1).strip()
            if not tail:
                return ParsedCommand(mentioned=True, help_requested=True)
            return self._parse_query(tail)

        if text.startswith(("查询", "配种")):
            return self._parse_query(text)

        return ParsedCommand(mentioned=False)

    def _parse_query(self, text: str) -> ParsedCommand:
        if text in {"查询", "配种"}:
            return ParsedCommand(mentioned=True, error=HELP_TEXT)

        match = re.match(r"^(查询|配种)(?:\s+|$)(.+)$", text)
        if not match:
            return ParsedCommand(mentioned=True, error=HELP_TEXT)

        kind_text = match.group(1)
        pet_name = match.group(2).strip()
        if not pet_name:
            return ParsedCommand(mentioned=True, error=HELP_TEXT)

        query = "breeding" if kind_text == "配种" else "body"
        return ParsedCommand(mentioned=True, query=query, pet_name=pet_name)
