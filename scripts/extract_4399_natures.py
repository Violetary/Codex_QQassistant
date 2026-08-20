from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract 4399 nature effects from inquiry page HTML")
    parser.add_argument("--html", default="data/raw/4399_inquiry.html")
    parser.add_argument("--output", default="data/natures.4399.json")
    args = parser.parse_args()

    text = Path(args.html).read_text(encoding="utf-8")
    match = NEXT_DATA_RE.search(text)
    if not match:
        raise SystemExit("cannot find __NEXT_DATA__ in HTML")

    payload = json.loads(html.unescape(match.group(1)))
    page_props = payload["props"]["pageProps"]
    modules = page_props["infoData"]
    item_module = find_module(modules, "items")
    filter_module = find_module(modules, "filter")

    filters = build_filter_map(filter_module["options"]["filters"])
    natures = []
    for item in item_module["options"]["items"]:
        category = {str(value) for value in item.get("category", [])}
        item_filters = [str(value) for value in item.get("filter", [])]
        if "2" not in category or len(item_filters) != 2:
            continue
        gain = normalize_stat(filters.get(item_filters[0], item_filters[0]))
        loss = normalize_stat(filters.get(item_filters[1], item_filters[1]))
        natures.append(
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
                "gain": gain,
                "loss": loss,
                "source": page_props["setting"]["web_url"],
            }
        )

    output = {
        "meta": {
            "source": page_props["setting"]["web_url"],
            "title": page_props["setting"]["seo_title"],
            "count": len(natures),
        },
        "natures": sorted(natures, key=lambda item: int(item["id"] or 0)),
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["meta"], ensure_ascii=False, indent=2))
    return 0


def find_module(modules: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for module in modules:
        if module.get("name") == name:
            return module
    raise KeyError(name)


def build_filter_map(filters: list[dict[str, Any]]) -> dict[str, str]:
    result = {}
    for group in filters:
        for child in group.get("children", []):
            result[str(child.get("id", ""))] = str(child.get("label", ""))
    return result


def normalize_stat(label: str) -> str:
    return (
        label.replace("增益", "")
        .replace("减益", "")
        .replace("生命", "精力")
        .strip()
    )


if __name__ == "__main__":
    raise SystemExit(main())
