from __future__ import annotations

from .base import DataSource, PetNotFound, SourceError
from rockbot.models import PetProfile


class CompositeSource(DataSource):
    name = "composite"

    def __init__(self, sources: list[DataSource]) -> None:
        self.sources = sources

    def fetch(self, pet_name: str) -> PetProfile:
        errors: list[str] = []
        for source in self.sources:
            try:
                return source.fetch(pet_name)
            except PetNotFound as exc:
                errors.append(f"{source.name}: {exc}")
            except SourceError as exc:
                errors.append(f"{source.name}: {exc}")
        detail = "; ".join(errors) if errors else "no sources configured"
        raise PetNotFound(f"未找到精灵 {pet_name}。{detail}")
