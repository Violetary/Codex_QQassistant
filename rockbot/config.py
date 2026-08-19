from __future__ import annotations

import json
from pathlib import Path

from .sources.web import WebSourceConfig


def load_web_sources(path: str | Path) -> list[WebSourceConfig]:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    configs: list[WebSourceConfig] = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "web"))
        url_template = str(item.get("url_template", ""))
        if not url_template:
            continue
        timeout = float(item.get("timeout_seconds", 8.0))
        configs.append(WebSourceConfig(name=name, url_template=url_template, timeout_seconds=timeout))
    return configs
