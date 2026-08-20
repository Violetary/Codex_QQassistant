from __future__ import annotations

import json
from pathlib import Path

from .base import DataSource, PetNotFound, SourceError
from rockbot.models import PetProfile


class LocalJsonSource(DataSource):
    name = "local-json"

    def __init__(self, path: str | Path = "data/pets.seed.json") -> None:
        self.path = Path(path)
        self._pets: dict[str, PetProfile] | None = None
        self._aliases: dict[str, PetProfile] | None = None

    def fetch(self, pet_name: str) -> PetProfile:
        aliases = self._load()
        profile = aliases.get(pet_name)
        if profile is None:
            raise PetNotFound(f"本地数据库没有 {pet_name}")
        return profile

    def _load(self) -> dict[str, PetProfile]:
        if self._aliases is not None:
            return self._aliases
        if not self.path.exists():
            raise SourceError(f"本地数据库不存在：{self.path}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceError(f"本地数据库读取失败：{exc}") from exc

        records = payload.get("pets", payload)
        if not isinstance(records, list):
            raise SourceError("本地数据库格式错误：pets 必须是数组")

        pets: dict[str, PetProfile] = {}
        aliases: dict[str, PetProfile] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            profile = PetProfile.from_dict(record)
            if profile.name:
                pets[profile.name] = profile
                aliases[profile.name] = profile
            for alias in profile.aliases + profile.evolution_chain + [stage.name for stage in profile.stages]:
                if alias:
                    aliases[alias] = profile
        self._pets = pets
        self._aliases = aliases
        return aliases
