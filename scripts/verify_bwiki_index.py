from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


API_URL = "https://wiki.biligame.com/rocom/api.php"
USER_AGENT = "rockbot-bwiki-index/1.0"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Compare local pet aliases with the public BWiki dex index.")
    parser.add_argument("--seed", default="data/pets.seed.json")
    parser.add_argument("--cache", default="data/raw/bwiki_dex_index.json")
    parser.add_argument("--report", default="outputs/bwiki_index_report.json")
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument(
        "--allow-missing",
        action="append",
        default=["宝藏小狐,宝藏沙狐,精灵筛选"],
        help="BWiki link title that is allowed to be absent locally",
    )
    args = parser.parse_args()

    seed = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    local_names = local_aliases(seed)
    bwiki_names = fetch_bwiki_index(Path(args.cache), force=args.force_fetch)

    allowed_missing = {name.strip() for item in args.allow_missing for name in item.split(",") if name.strip()}
    missing_locally = sorted((bwiki_names - local_names) - allowed_missing)
    not_on_bwiki = sorted(local_names - bwiki_names)
    report = {
        "ok": not missing_locally,
        "local_name_count": len(local_names),
        "bwiki_name_count": len(bwiki_names),
        "missing_locally_count": len(missing_locally),
        "allowed_missing_count": len(allowed_missing & bwiki_names),
        "not_on_bwiki_count": len(not_on_bwiki),
        "missing_locally": missing_locally,
        "allowed_missing": sorted(allowed_missing & bwiki_names),
        "not_on_bwiki": not_on_bwiki,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, list)}, ensure_ascii=False, indent=2))
    return 0 if not missing_locally else 1


def local_aliases(seed: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for family in seed.get("pets", []):
        candidates = [
            family.get("name", ""),
            *family.get("aliases", []),
            *family.get("evolution_chain", []),
            *(stage.get("name", "") for stage in family.get("stages", [])),
        ]
        names.update(str(name).strip() for name in candidates if str(name).strip())
    return names


def fetch_bwiki_index(cache_path: Path, force: bool) -> set[str]:
    if cache_path.exists() and not force:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        query = urllib.parse.urlencode(
            {
                "action": "parse",
                "page": "精灵图鉴",
                "prop": "links",
                "format": "json",
            }
        )
        request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    links = payload.get("parse", {}).get("links", [])
    return {
        str(link.get("*", "")).strip()
        for link in links
        if isinstance(link, dict) and int(link.get("ns", -1)) == 0 and str(link.get("*", "")).strip()
    }


if __name__ == "__main__":
    raise SystemExit(main())
