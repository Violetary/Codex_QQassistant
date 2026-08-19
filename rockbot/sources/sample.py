from __future__ import annotations

from .base import DataSource, PetNotFound
from rockbot.models import PetProfile, PvpRecommendation, StageBody


class SampleSource(DataSource):
    name = "sample"

    def __init__(self) -> None:
        self._pets = {
            "奇丽草": PetProfile(
                name="奇丽草",
                source=self.name,
                evolution_chain=["奇丽草", "奇丽叶", "奇丽花"],
                pvp=PvpRecommendation(
                    nature="保守 / 胆小",
                    attributes="魔攻、速度优先；精力按玩法补足",
                    notes="示例数据，仅用于本地流程验证。真实推荐需接入资料源。",
                ),
                stages=[
                    StageBody("奇丽草", "植物组", "0.16-0.23", "1.4350-2.2800", "2.2631", "1.4519"),
                    StageBody("奇丽叶", "植物组", "0.62-0.89", "24-31", "30.8600", "24.1400"),
                    StageBody("奇丽花", "植物组", "1.11-1.58", "42-58", "57.6800", "42.3200"),
                ],
            )
        }

    def fetch(self, pet_name: str) -> PetProfile:
        profile = self._pets.get(pet_name)
        if profile is None:
            raise PetNotFound(f"示例源没有 {pet_name}")
        return profile
