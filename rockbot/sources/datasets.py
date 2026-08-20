from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FormStats:
    name: str
    big_body: float | None = None
    limit_value: float | None = None
    interval: float | None = None
    interval_count: float | None = None
    aliases: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormStats":
        return cls(
            name=str(data.get("name", "")),
            big_body=_as_float(data.get("big_body")),
            limit_value=_as_float(data.get("limit_value")),
            interval=_as_float(data.get("interval")),
            interval_count=_as_float(data.get("interval_count")),
            aliases=[str(item) for item in data.get("aliases", []) if str(item)],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "big_body": self.big_body,
            "limit_value": self.limit_value,
            "interval": self.interval,
            "interval_count": self.interval_count,
            "aliases": self.aliases,
        }


@dataclass(slots=True)
class PetFamily:
    family_name: str
    forms: list[FormStats] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PetFamily":
        return cls(
            family_name=str(data.get("family_name", data.get("name", ""))),
            forms=[FormStats.from_dict(item) for item in data.get("forms", []) if isinstance(item, dict)],
            aliases=[str(item) for item in data.get("aliases", []) if str(item)],
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "family_name": self.family_name,
            "forms": [form.to_dict() for form in self.forms],
            "aliases": self.aliases,
        }
        return payload


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
