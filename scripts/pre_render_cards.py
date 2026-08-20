from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rockbot.models import PetProfile
from rockbot.render import CardRenderer


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-render all Rock Kingdom bot cards")
    parser.add_argument("--database", default="data/pets.seed.json")
    parser.add_argument("--output-dir", default="outputs/cards")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.database).read_text(encoding="utf-8"))
    renderer = CardRenderer(args.output_dir)
    count = 0
    for item in payload.get("pets", []):
        if not isinstance(item, dict):
            continue
        profile = PetProfile.from_dict(item)
        renderer.render(profile, "body", force=args.force)
        count += 1
    print(json.dumps({"rendered": count, "output_dir": str(Path(args.output_dir).resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
