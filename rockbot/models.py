from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


QueryKind = Literal["pvp", "egg"]


@dataclass(slots=True)
class StageBody:
    name: str
    egg_group: str
    height_range: str
    weight_range: str
    big_body_range: str
    small_body_range: str
    form_id: int | None = None
    types: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageBody":
        return cls(
            name=str(data.get("name", "")),
            egg_group=str(data.get("egg_group", "未知")),
            height_range=str(data.get("height_range", "未知")),
            weight_range=str(data.get("weight_range", "未知")),
            big_body_range=str(data.get("big_body_range", "未知")),
            small_body_range=str(data.get("small_body_range", "未知")),
            form_id=int(data["form_id"]) if data.get("form_id") not in (None, "") else None,
            types=[str(item) for item in data.get("types", []) if str(item)],
        )


@dataclass(slots=True)
class PvpRecommendation:
    nature: str
    attributes: str
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PvpRecommendation":
        return cls(
            nature=str(data.get("nature", "暂无推荐")),
            attributes=str(data.get("attributes", "暂无推荐")),
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class PetProfile:
    name: str
    source: str
    family_id: int | None = None
    evolution_chain: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    pvp: PvpRecommendation | None = None
    stages: list[StageBody] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PetProfile":
        pvp_data = data.get("pvp")
        return cls(
            name=str(data.get("name", "")),
            source=str(data.get("source", "unknown")),
            family_id=int(data["family_id"]) if data.get("family_id") not in (None, "") else None,
            evolution_chain=[str(item) for item in data.get("evolution_chain", [])],
            aliases=[str(item) for item in data.get("aliases", []) if str(item)],
            pvp=PvpRecommendation.from_dict(pvp_data) if isinstance(pvp_data, dict) else None,
            stages=[StageBody.from_dict(item) for item in data.get("stages", []) if isinstance(item, dict)],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParsedCommand:
    mentioned: bool
    query: QueryKind | None = None
    pet_name: str | None = None
    help_requested: bool = False
    error: str | None = None


@dataclass(slots=True)
class BotReply:
    text: str
    image_path: str | None = None
    ok: bool = True
