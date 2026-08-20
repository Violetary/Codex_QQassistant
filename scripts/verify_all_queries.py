from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rockbot.cache import JsonCache
from rockbot.render import CardRenderer
from rockbot.service import BotService
from rockbot.sources import CompositeSource, LocalJsonSource


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify every local pet alias can return egg and PVP cards.")
    parser.add_argument("--database", default="data/pets.seed.json")
    parser.add_argument("--output-dir", default="outputs/cards")
    parser.add_argument("--cache-dir", default="data/cache")
    parser.add_argument("--limit", type=int, default=0, help="verify only the first N unique names")
    args = parser.parse_args()

    db_path = Path(args.database)
    payload = json.loads(db_path.read_text(encoding="utf-8"))
    names = unique_query_names(payload)
    if args.limit:
        names = names[: args.limit]

    service = BotService(
        cache=JsonCache(args.cache_dir),
        source=CompositeSource([LocalJsonSource(db_path)]),
        renderer=CardRenderer(args.output_dir),
    )

    failures: list[dict[str, str]] = []
    started = time.perf_counter()
    for name in names:
        for action in ("查蛋", "pvp", "PVP"):
            message = f"@友哈巴赫 {name} {action}"
            reply = service.handle_message(message)
            if reply is None or not reply.ok or not reply.image_path or not Path(reply.image_path).exists():
                failures.append(
                    {
                        "name": name,
                        "action": action,
                        "text": "" if reply is None else reply.text,
                        "image_path": "" if reply is None or reply.image_path is None else reply.image_path,
                    }
                )

    elapsed = time.perf_counter() - started
    result = {
        "ok": not failures,
        "names": len(names),
        "checks": len(names) * 3,
        "seconds": round(elapsed, 3),
        "avg_ms": round(elapsed * 1000 / max(1, len(names) * 3), 2),
        "failures": failures[:20],
        "failure_count": len(failures),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


def unique_query_names(payload: dict) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for family in payload.get("pets", []):
        candidates = [
            family.get("name", ""),
            *family.get("aliases", []),
            *family.get("evolution_chain", []),
            *(stage.get("name", "") for stage in family.get("stages", [])),
        ]
        for candidate in candidates:
            name = str(candidate).strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names


if __name__ == "__main__":
    raise SystemExit(main())
