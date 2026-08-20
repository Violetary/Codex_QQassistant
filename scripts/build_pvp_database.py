from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STAT_LABELS = {
    "hp": "精力",
    "atk": "物攻",
    "def": "物防",
    "sp_atk": "魔攻",
    "sp_def": "魔防",
    "speed": "速度",
}

LOSS_BY_ATTACK = {
    "physical": "魔攻",
    "magical": "物攻",
    "mixed": "物防",
    "tank": "速度",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build auditable PVP recommendation database")
    parser.add_argument("--pets-source", default="data/raw/roco_egg_master/src/pets_data.json")
    parser.add_argument("--natures", default="data/natures.4399.json")
    parser.add_argument("--seed", default="data/pets.seed.json")
    parser.add_argument("--output", default="data/pvp.recommendations.json")
    args = parser.parse_args()

    pets_source = json.loads(read_text(Path(args.pets_source)))
    natures = json.loads(Path(args.natures).read_text(encoding="utf-8"))["natures"]
    records = []
    pvp_by_family = {}

    for pet in pets_source:
        forms = flatten_forms(pet)
        if not forms:
            continue
        core = max(forms, key=stat_sum)
        recommendation = recommend(core, natures)
        record = {
            "family_id": pet.get("id"),
            "family_name": pet.get("name"),
            "core_form": core.get("name"),
            "core_form_id": core.get("id"),
            "types": [str(item) for item in core.get("types", [])],
            "stats": normalize_stats(core.get("stats", {})),
            **recommendation,
            "source": {
                "stats": "roco_egg_master/src/pets_data.json",
                "nature_mechanics": json.loads(Path(args.natures).read_text(encoding="utf-8"))["meta"]["source"],
                "method": "rules-v1",
            },
        }
        records.append(record)
        pvp_by_family[str(pet.get("id"))] = record

    output = {
        "meta": {
            "record_count": len(records),
            "source": "computed from real base stats and 4399 nature mechanics",
            "method": "rules-v1",
            "notes": "This is an auditable baseline recommendation. Manual overrides can replace any family later with cited guide sources.",
        },
        "records": records,
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    merge_into_seed(Path(args.seed), pvp_by_family)
    print(json.dumps(output["meta"], ensure_ascii=False, indent=2))
    return 0


def recommend(form: dict[str, Any], natures: list[dict[str, Any]]) -> dict[str, Any]:
    stats = normalize_stats(form.get("stats", {}))
    attack_style = choose_attack_style(stats)
    primary = "魔攻" if attack_style == "magical" else "物攻" if attack_style == "physical" else "速度"
    if attack_style == "tank":
        primary = best_defense(stats)

    priorities = choose_priorities(stats, attack_style)
    nature_names = pick_natures(natures, priorities[:2], LOSS_BY_ATTACK[attack_style])
    if not nature_names:
        nature_names = pick_natures(natures, [primary], LOSS_BY_ATTACK[attack_style])

    notes = [
        f"核心形态：{form.get('name')}",
        f"判断依据：{describe_style(attack_style)}，六维最高项为 {highest_stat(stats)}。",
        "该推荐由真实六维与性格增减益规则计算，尚未加入社区配招人工校正。",
    ]
    return {
        "nature": " / ".join(nature_names) if nature_names else "待人工校正",
        "attributes": "、".join(priorities),
        "notes": " ".join(notes),
        "confidence": "computed",
    }


def choose_attack_style(stats: dict[str, int]) -> str:
    atk = stats.get("atk", 0)
    sp_atk = stats.get("sp_atk", 0)
    speed = stats.get("speed", 0)
    offense = max(atk, sp_atk)
    defense = max(stats.get("hp", 0), stats.get("def", 0), stats.get("sp_def", 0))
    if defense >= offense + 20 and speed < offense:
        return "tank"
    if abs(atk - sp_atk) <= 12 and offense >= 90:
        return "mixed"
    if sp_atk >= atk:
        return "magical"
    return "physical"


def choose_priorities(stats: dict[str, int], attack_style: str) -> list[str]:
    if attack_style == "magical":
        base = ["魔攻", "速度" if stats.get("speed", 0) >= 80 else "精力", best_defense(stats)]
    elif attack_style == "physical":
        base = ["物攻", "速度" if stats.get("speed", 0) >= 80 else "精力", best_defense(stats)]
    elif attack_style == "mixed":
        base = ["速度", "物攻", "魔攻"]
    else:
        base = [best_defense(stats), "精力", "速度" if stats.get("speed", 0) >= 70 else "物防"]
    return dedupe(base)


def pick_natures(natures: list[dict[str, Any]], gains: list[str], loss: str) -> list[str]:
    result = []
    for gain in gains:
        for nature in natures:
            if nature.get("gain") == gain and nature.get("loss") == loss:
                result.append(str(nature["name"]))
                break
    return dedupe(result)[:3]


def best_defense(stats: dict[str, int]) -> str:
    return "物防" if stats.get("def", 0) >= stats.get("sp_def", 0) else "魔防"


def highest_stat(stats: dict[str, int]) -> str:
    key = max((key for key in STAT_LABELS if key in stats), key=lambda key: stats[key])
    return f"{STAT_LABELS[key]}({stats[key]})"


def describe_style(style: str) -> str:
    return {
        "magical": "魔攻向",
        "physical": "物攻向",
        "mixed": "双攻/高速向",
        "tank": "耐久向",
    }[style]


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


def stat_sum(form: dict[str, Any]) -> int:
    stats = normalize_stats(form.get("stats", {}))
    return stats.get("sum") or sum(stats.values())


def normalize_stats(stats: dict[str, Any]) -> dict[str, int]:
    nested = stats.get("stats") if isinstance(stats.get("stats"), dict) else stats
    result = {}
    for key in list(STAT_LABELS) + ["sum"]:
        value = nested.get(key) if isinstance(nested, dict) else None
        if value is not None:
            result[key] = int(value)
    if "sum" not in result and result:
        result["sum"] = sum(value for key, value in result.items() if key != "sum")
    return result


def merge_into_seed(seed_path: Path, pvp_by_family: dict[str, dict[str, Any]]) -> None:
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    matched = 0
    for pet in seed.get("pets", []):
        family_id = str(pet.get("family_id"))
        pvp = pvp_by_family.get(family_id)
        if not pvp:
            continue
        pet["pvp"] = {
            "nature": pvp["nature"],
            "attributes": pvp["attributes"],
            "notes": pvp["notes"],
        }
        matched += 1
    seed.setdefault("meta", {})["pvp"] = {
        "matched_family_count": matched,
        "source": "data/pvp.recommendations.json",
        "method": "rules-v1",
    }
    seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
