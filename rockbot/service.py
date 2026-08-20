from __future__ import annotations

from pathlib import Path

from .cache import JsonCache
from .models import BotReply, ParsedCommand, PetProfile
from .parser import HELP_TEXT, CommandParser
from .render import CardRenderer
from .sources import CompositeSource, DataSource, LocalJsonSource, PetNotFound, SampleSource, SourceError


class BotService:
    def __init__(
        self,
        bot_name: str = "友哈巴赫",
        cache: JsonCache | None = None,
        source: DataSource | None = None,
        renderer: CardRenderer | None = None,
    ) -> None:
        self.parser = CommandParser(bot_name=bot_name)
        self.cache = cache or JsonCache()
        self.source = source or CompositeSource([LocalJsonSource(), SampleSource()])
        self.renderer = renderer or CardRenderer()

    def handle_message(self, message: str) -> BotReply | None:
        command = self.parser.parse(message)
        if not command.mentioned:
            return None
        if command.help_requested:
            return BotReply(text=HELP_TEXT)
        if command.error:
            return BotReply(text=command.error, ok=False)
        if not command.pet_name or not command.query:
            return BotReply(text=HELP_TEXT, ok=False)

        try:
            profile = self._get_profile(command.pet_name)
        except PetNotFound:
            return BotReply(text=f"没有查到“{command.pet_name}”。可以换个精灵名，或先补真实资料源。", ok=False)
        except SourceError as exc:
            return BotReply(text=f"数据源暂时不可用：{exc}", ok=False)

        image_path = self.renderer.render(profile, command.query)
        return BotReply(text="", image_path=str(Path(image_path).resolve()))

    def _get_profile(self, pet_name: str) -> PetProfile:
        try:
            profile = self.source.fetch(pet_name)
        except PetNotFound:
            cached = self.cache.get(pet_name)
            if cached and not self._is_stale_profile(cached):
                return cached
            raise
        if self._should_persist_profile(profile):
            self.cache.set(profile)
        return profile

    def _is_stale_profile(self, profile: PetProfile) -> bool:
        if not any(stage.is_egg for stage in profile.stages):
            return True
        return not profile.stages

    def _should_persist_profile(self, profile: PetProfile) -> bool:
        return profile.source not in {"local-seed", "sample"}

    def _summary(self, profile: PetProfile, command: ParsedCommand) -> str:
        return f"{profile.name} 的身高体重数据已生成。"
