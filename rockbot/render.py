from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .models import PetProfile, QueryKind, StageBody


class CardRenderer:
    def __init__(self, output_dir: str | Path = "outputs") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_regular = self._font(28)
        self.font_medium = self._font(30, bold=True)
        self.font_title = self._font(38, bold=True)
        self.font_small = self._font(22)
        self.font_tiny = self._font(18)

    def render(self, profile: PetProfile, query: QueryKind) -> Path:
        rows = self._rows(profile, query)
        height = self._height(rows, query)
        image = Image.new("RGB", (760, height), "#120923")
        draw = ImageDraw.Draw(image)

        self._draw_header(draw, profile, query)
        if query == "pvp":
            self._draw_pvp(draw, rows)
        else:
            self._draw_egg(draw, rows)

        footer = f"source: {profile.source}"
        draw.text((54, height - 44), footer, font=self.font_small, fill="#8f85a8")

        output = self.output_dir / f"{profile.name}_{query}.png"
        image.save(output)
        return output

    def _height(self, rows: list[tuple[str, str]], query: QueryKind) -> int:
        if query == "pvp":
            return 460 + len(rows) * 34
        stage_count = sum(1 for kind, _ in rows if kind == "stage")
        return max(960, 250 + stage_count * 240)

    def _draw_header(self, draw: ImageDraw.ImageDraw, profile: PetProfile, query: QueryKind) -> None:
        label = "PVP 推荐" if query == "pvp" else "蛋组与体型"
        draw.rectangle((0, 0, 760, 92), fill="#21104a")
        draw.rectangle((0, 92, 760, 98), fill="#8f7cff")
        draw.line((54, 122, 706, 122), fill="#3a245f", width=1)
        title = f"查询 · {profile.name}"
        draw.text((54, 28), title, font=self.font_title, fill="#ffffff")
        draw.text((580, 34), label, font=self.font_small, fill="#d7ccff")

    def _rows(self, profile: PetProfile, query: QueryKind) -> list[tuple[str, str]]:
        if query == "pvp":
            pvp = profile.pvp
            if not pvp:
                return [("section", "PVP 推荐"), ("text", "暂无 PVP 推荐数据")]
            rows = [
                ("section", "PVP 推荐"),
                ("text", f"性格：{pvp.nature}"),
                ("text", f"属性：{pvp.attributes}"),
            ]
            if pvp.notes:
                rows.append(("muted", pvp.notes))
            return rows

        rows: list[tuple[str, str]] = [("section", "蛋组与体型数据")]
        if profile.evolution_chain:
            rows.append(("accent", "进化链：" + " -> ".join(profile.evolution_chain)))
        if not profile.stages:
            rows.append(("text", "暂无蛋组与体型数据"))
            return rows
        for stage in profile.stages:
            rows.append(("stage", stage.name))
            rows.append(("stage_text", f"蛋组：{stage.egg_group}"))
            rows.append(("stage_text", f"身高：{stage.height_range} | 体重：{stage.weight_range}"))
            rows.append(("stage_text", f"大块头：{stage.big_body_range} | 小不点：{stage.small_body_range}"))
        return rows

    def _draw_pvp(self, draw: ImageDraw.ImageDraw, rows: list[tuple[str, str]]) -> None:
        draw.rounded_rectangle((44, 154, 716, 372), radius=18, fill="#1a0f35", outline="#4c2c78", width=2)
        y = 182
        for kind, text in rows:
            if kind == "section":
                draw.text((70, y), text, font=self.font_medium, fill="#ffffff")
                y += 52
            elif kind == "text":
                for line in self._wrap(text, 34):
                    draw.text((72, y), line, font=self.font_regular, fill="#f4efff")
                    y += 42
            elif kind == "muted":
                for line in self._wrap(text, 38):
                    draw.text((72, y), line, font=self.font_tiny, fill="#a79abd")
                    y += 30

    def _draw_egg(self, draw: ImageDraw.ImageDraw, rows: list[tuple[str, str]]) -> None:
        y = 152
        stage_box_top = None
        current_stage = None
        stage_lines: list[str] = []

        def flush_stage() -> None:
            nonlocal y, stage_box_top, current_stage, stage_lines
            if current_stage is None or stage_box_top is None:
                return
            wrapped_lines = [line for text in stage_lines for line in self._wrap(text, 34)]
            box_height = 92 + max(1, len(wrapped_lines)) * 38
            box_bottom = stage_box_top + box_height
            draw.rounded_rectangle((44, stage_box_top, 716, box_bottom), radius=18, fill="#1a0f35", outline="#4c2c78", width=2)
            draw.text((68, stage_box_top + 20), current_stage, font=self.font_medium, fill="#ffffff")
            line_y = stage_box_top + 68
            for line in wrapped_lines:
                draw.text((72, line_y), line, font=self.font_regular, fill="#f4efff")
                line_y += 40
            y = box_bottom + 16
            stage_box_top = None
            current_stage = None
            stage_lines = []

        for kind, text in rows:
            if kind == "section":
                draw.text((54, y), text, font=self.font_medium, fill="#ffffff")
                y += 52
            elif kind == "accent":
                draw.text((54, y), text, font=self.font_regular, fill="#f472d0")
                y += 48
            elif kind == "stage":
                flush_stage()
                current_stage = text
                stage_box_top = y
                stage_lines = []
            elif kind == "stage_text":
                stage_lines.extend(self._wrap(text, 34))
            elif kind == "text":
                for line in self._wrap(text, 36):
                    draw.text((70, y), line, font=self.font_regular, fill="#f4efff")
                    y += 42
            elif kind == "muted":
                for line in self._wrap(text, 38):
                    draw.text((54, y), line, font=self.font_tiny, fill="#a79abd")
                    y += 30
        flush_stage()

    def _wrap(self, text: str, width: int) -> Iterable[str]:
        return textwrap.wrap(text, width=width, replace_whitespace=False) or [""]

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = [
            "C:/Windows/Fonts/NotoSansSC-VF.ttf",
            "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
        ]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()
