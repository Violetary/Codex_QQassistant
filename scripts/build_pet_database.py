from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local Rock Kingdom pet database")
    parser.add_argument("--source", default="data/raw/roco_egg_master/src/pets_data.json")
    parser.add_argument("--body-xls", default="data/raw/big_body_ranges.xls")
    parser.add_argument("--output", default="data/pets.seed.json")
    parser.add_argument("--limit", type=int, default=442, help="target form count for the first database")
    args = parser.parse_args()

    source_path = Path(args.source)
    body_rows = load_body_xls(Path(args.body_xls))
    pets_data = json.loads(read_text(source_path))

    families = []
    form_count = 0
    for pet in pets_data:
        if form_count >= args.limit:
            break
        profile = build_profile(pet, body_rows)
        if not profile["stages"]:
            continue
        if form_count + len(profile["stages"]) > args.limit:
            profile["stages"] = profile["stages"][: args.limit - form_count]
            profile["evolution_chain"] = [stage["name"] for stage in profile["stages"]]
            profile["aliases"] = sorted(set(profile["evolution_chain"]))
        families.append(profile)
        form_count += len(profile["stages"])

    output = {
        "meta": {
            "source": "roco_egg_master + user big-body xls reference",
            "family_count": len(families),
            "form_count": form_count,
            "target_form_count": args.limit,
            "notes": "Every form name is indexed as an alias of its family profile.",
        },
        "pets": families,
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["meta"], ensure_ascii=False, indent=2))
    return 0


def build_profile(pet: dict[str, Any], body_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    family_name = str(pet.get("name", ""))
    forms = flatten_forms(pet)
    stages = [build_stage(form, body_rows) for form in forms if form.get("name")]
    aliases = sorted({stage["name"] for stage in stages} | set(flatten_chain(pet.get("evolution_chain", []))))
    return {
        "family_id": pet.get("id"),
        "name": family_name,
        "source": "local-seed",
        "evolution_chain": flatten_chain(pet.get("evolution_chain", [])) or [stage["name"] for stage in stages],
        "aliases": aliases,
        "pvp": {
            "nature": "待补充",
            "attributes": "待补充",
            "notes": "当前数据库先补全蛋组与体型；PVP 推荐后续单独导入。",
        },
        "stages": stages,
    }


def flatten_forms(pet: dict[str, Any]) -> list[dict[str, Any]]:
    forms: list[dict[str, Any]] = []
    if pet.get("forms"):
        forms.extend(item for item in pet["forms"] if isinstance(item, dict))
    else:
        forms.append(pet)
    for key in ("other_forms", "lord_forms", "regional_forms"):
        forms.extend(item for item in pet.get(key, []) if isinstance(item, dict))
    seen = set()
    ordered = []
    for form in forms:
        name = form.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(form)
    return ordered


def build_stage(form: dict[str, Any], body_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    name = str(form.get("name", ""))
    body = body_rows.get(name, {})
    egg_groups = form.get("egg_groups") or form.get("egg_data", {}).get("egg_groups") or ["未知"]
    return {
        "form_id": form.get("id"),
        "name": name,
        "types": [str(item) for item in form.get("types", [])],
        "egg_group": "、".join(str(item) for item in egg_groups),
        "height_range": format_range(form.get("height_min"), form.get("height_max")),
        "weight_range": format_range(form.get("weight_min"), form.get("weight_max")),
        "big_body_range": format_number(body.get("big_body", form.get("giant_weight_line"))),
        "small_body_range": format_number(form.get("tiny_weight_line")),
    }


def flatten_chain(chain: list[Any]) -> list[str]:
    result: list[str] = []
    for item in chain:
        if isinstance(item, list):
            result.extend(flatten_chain(item))
        elif item:
            result.append(str(item))
    return result


def load_body_xls(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    sys.path.insert(0, str(Path(".deps").resolve()))
    try:
        import xlrd  # type: ignore
    except ImportError:
        return {}
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)
    rows: dict[str, dict[str, Any]] = {}
    for r in range(1, sh.nrows):
        name = str(sh.cell_value(r, 1)).strip()
        if not name:
            continue
        rows[name] = {
            "tier": str(sh.cell_value(r, 0)).strip(),
            "big_body": as_float(sh.cell_value(r, 2)),
            "limit_value": as_float(sh.cell_value(r, 3)),
            "interval": as_float(sh.cell_value(r, 4)),
            "interval_count": as_float(sh.cell_value(r, 5)),
        }
    return rows


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def as_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_range(low: Any, high: Any) -> str:
    if low in ("", None) or high in ("", None):
        return "未知"
    return f"{format_number(low)}-{format_number(high)}"


def format_number(value: Any) -> str:
    if value in ("", None):
        return "未知"
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
