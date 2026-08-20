from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


API_URL = "https://wiki.biligame.com/rocom/api.php"
USER_AGENT = "rockbot-body-sync/1.0"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Sync form height/weight from BWiki Rock Kingdom pages.")
    parser.add_argument("--seed", default="data/pets.seed.json")
    parser.add_argument("--cache-dir", default="data/raw/bwiki_pages")
    parser.add_argument("--report", default="outputs/bwiki_body_sync_report.json")
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-fetch", action="store_true")
    args = parser.parse_args()

    seed_path = Path(args.seed)
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    stages = [
        stage
        for family in payload.get("pets", [])
        for stage in family.get("stages", [])
        if isinstance(stage, dict) and not stage.get("is_egg") and stage.get("name")
    ]
    if args.limit:
        stages = stages[: args.limit]

    updates: list[dict[str, str]] = []
    missing: list[str] = []
    errors: list[dict[str, str]] = []
    started = time.perf_counter()

    fields_by_name = fetch_all_fields(
        [str(stage["name"]).strip() for stage in stages],
        cache_dir=cache_dir,
        force=args.force_fetch,
        workers=max(1, args.workers),
        retries=max(0, args.retries),
        delay=args.delay,
        missing=missing,
        errors=errors,
    )

    for stage in stages:
        name = str(stage["name"]).strip()
        fields = fields_by_name.get(name)
        if not fields:
            continue
        height = normalize_range(fields.get("体型", ""))
        weight = normalize_range(fields.get("重量", ""))
        for key, value in (("height_range", height), ("weight_range", weight)):
            if not value or value == stage.get(key):
                continue
            updates.append(
                {
                    "name": name,
                    "field": key,
                    "old": str(stage.get(key, "")),
                    "new": value,
                }
            )
            if not args.dry_run:
                stage[key] = value

    if not args.dry_run:
        meta = payload.setdefault("meta", {})
        meta["body_sync"] = {
            "source": "BWiki 洛克王国手游 WIKI MediaWiki API",
            "checked_form_count": len(stages),
            "updated_field_count": len(updates),
            "missing_page_count": len(missing),
        }
        seed_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "ok": not errors,
        "dry_run": args.dry_run,
        "checked_form_count": len(stages),
        "updated_field_count": len(updates),
        "missing_page_count": len(missing),
        "error_count": len(errors),
        "seconds": round(time.perf_counter() - started, 3),
        "updates": updates,
        "missing": missing,
        "errors": errors,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key not in {"updates", "missing", "errors"}}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


class PageMissing(RuntimeError):
    pass


def fetch_all_fields(
    names: list[str],
    cache_dir: Path,
    force: bool,
    workers: int,
    retries: int,
    delay: float,
    missing: list[str],
    errors: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    fields_by_name: dict[str, dict[str, str]] = {}
    if workers == 1:
        for index, name in enumerate(names, start=1):
            try:
                fields_by_name[name] = fetch_bwiki_fields(name, cache_dir, force=force, retries=retries)
            except PageMissing:
                missing.append(name)
            except Exception as exc:  # noqa: BLE001
                errors.append({"name": name, "error": str(exc)})
            if delay and index < len(names):
                time.sleep(delay)
        return fields_by_name

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_bwiki_fields, name, cache_dir, force, retries): name for name in names}
        for future in as_completed(futures):
            name = futures[future]
            try:
                fields_by_name[name] = future.result()
            except PageMissing:
                missing.append(name)
            except Exception as exc:  # noqa: BLE001
                errors.append({"name": name, "error": str(exc)})
    return fields_by_name


def fetch_bwiki_fields(name: str, cache_dir: Path, force: bool = False, retries: int = 4) -> dict[str, str]:
    cache_path = cache_dir / f"{safe_filename(name)}.json"
    if cache_path.exists() and not force:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        query = urllib.parse.urlencode(
            {
                "action": "parse",
                "page": name,
                "prop": "wikitext",
                "format": "json",
            }
        )
        request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
        payload = request_json(request, retries=retries)
        if "error" in payload:
            code = str(payload["error"].get("code", ""))
            if code == "missingtitle":
                raise PageMissing(name)
            raise RuntimeError(payload["error"])
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    wikitext = payload.get("parse", {}).get("wikitext", {}).get("*", "")
    if not isinstance(wikitext, str) or not wikitext:
        raise RuntimeError(f"{name} 页面没有 wikitext")
    return parse_template_fields(wikitext)


def request_json(request: urllib.request.Request, retries: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise PageMissing(request.full_url) from exc
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504, 514, 567}:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(min(8.0, 0.6 * (2**attempt)))
    if last_error is not None:
        raise last_error
    raise RuntimeError("empty request failure")


def parse_template_fields(wikitext: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in wikitext.splitlines():
        match = re.match(r"^\|([^=]+)=(.*)$", line.strip())
        if not match:
            continue
        fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def normalize_range(value: str) -> str:
    value = value.strip().replace("～", "~").replace("—", "-").replace("－", "-")
    value = value.replace(" ~ ", "~").replace(" - ", "-")
    value = value.replace("~", "-")
    parts = value.split("-")
    if len(parts) == 2:
        return "-".join(normalize_number(part) for part in parts)
    return value


def normalize_number(value: str) -> str:
    value = value.strip()
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def safe_filename(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._") or "page"


if __name__ == "__main__":
    raise SystemExit(main())
