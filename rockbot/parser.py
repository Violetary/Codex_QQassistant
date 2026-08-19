from __future__ import annotations

import re

from .models import ParsedCommand


HELP_TEXT = "请按格式输入：@友哈巴赫 精灵名 pvp 或 @友哈巴赫 精灵名 查蛋"


class CommandParser:
    def __init__(self, bot_name: str = "友哈巴赫") -> None:
        self.bot_name = bot_name
        self._mention_pattern = re.compile(rf"^\s*@{re.escape(bot_name)}(?:\s+|$)(.*)$", re.IGNORECASE)

    def parse(self, message: str) -> ParsedCommand:
        match = self._mention_pattern.match(message or "")
        if not match:
            return ParsedCommand(mentioned=False)

        tail = match.group(1).strip()
        if not tail:
            return ParsedCommand(mentioned=True, help_requested=True)

        parts = tail.split()
        if len(parts) < 2:
            return ParsedCommand(mentioned=True, error=HELP_TEXT)

        action = parts[-1].lower()
        pet_name = " ".join(parts[:-1]).strip()
        if not pet_name:
            return ParsedCommand(mentioned=True, error=HELP_TEXT)

        if action in {"pvp", "性格", "性格推荐", "推荐"}:
            return ParsedCommand(mentioned=True, query="pvp", pet_name=pet_name)
        if action in {"查蛋", "蛋", "蛋组", "体型"}:
            return ParsedCommand(mentioned=True, query="egg", pet_name=pet_name)

        return ParsedCommand(mentioned=True, error=HELP_TEXT)
