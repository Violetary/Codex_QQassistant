from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rockbot.models import BotReply
from rockbot.service import BotService


@dataclass(slots=True)
class QQMessage:
    raw_text: str
    group_id: str | None = None
    user_id: str | None = None


class QQAdapter(Protocol):
    """Protocol for future NapCat/OneBot/official QQ adapters."""

    service: BotService

    def handle(self, message: QQMessage) -> BotReply | None:
        ...
