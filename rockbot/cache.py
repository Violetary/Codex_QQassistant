from __future__ import annotations

import json
import re
from pathlib import Path

from .models import PetProfile


class JsonCache:
    def __init__(self, root: str | Path = "data/cache") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, pet_name: str) -> PetProfile | None:
        path = self._path_for(pet_name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return PetProfile.from_dict(data)

    def set(self, profile: PetProfile) -> None:
        payload = json.dumps(profile.to_dict(), ensure_ascii=False, indent=2)
        names = {profile.name, *profile.aliases, *profile.evolution_chain, *(stage.name for stage in profile.stages)}
        for name in names:
            path = self._path_for(name)
            path.write_text(payload, encoding="utf-8")

    def delete(self, pet_name: str) -> None:
        path = self._path_for(pet_name)
        if path.exists():
            path.unlink()

    def _path_for(self, pet_name: str) -> Path:
        slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", pet_name).strip("_")
        return self.root / f"{slug or 'unknown'}.json"
