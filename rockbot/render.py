from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .models import PetProfile, QueryKind, StageBody


class CardRenderer:
    version = "v3"

    def __init__(self, output_dir: str | Path = "outputs/cards") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_title = self._font(34, bold=True)
        self.font_label = self._font(22, bold=True)
        self.font_body = self._font(24)
        self.font_small = self._font(19)
        self.font_tiny = self._font(16)
        self.colors = {
            "bg": "#111614",
            "header": "#18211f",
            "panel": "#1d2724",
            "panel_alt": "#202b28",
            "border": "#3e5d55",
            "accent": "#c8a968",
            "accent_2": "#7fb7a3",
            "text": "#eef2eb",
            "muted": "#aab5ad",
            "subtle": "#6f7c75",
            "line": "#2b3935",
        }

    def render(self, profile: PetProfile, query: QueryKind, force: bool = False) -> Path:
        output = self.output_path(profile, query)
        if output.exists() and not force:
            return output

        if query == "pvp":
            image = self._render_pvp(profile)
        else:
            image = self._render_egg(profile)
        image.save(output, optimize=True)
        return output

    def output_path(self, profile: PetProfile, query: QueryKind) -> Path:
        prefix = str(profile.family_id) if profile.family_id is not None else profile.name
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", prefix).strip() or "pet"
        return self.output_dir / f"{safe_name}_{query}_{self.version}.png"

    def _render_pvp(self, profile: PetProfile) -> Image.Image:
        pvp = profile.pvp
        title_lines = [("性格", pvp.nature if pvp else "暂无推荐"), ("属性", pvp.attributes if pvp else "暂无推荐")]
        note_lines: list[str] = []
        panel_height = 118 + len(note_lines) * 26
        height = 128 + panel_height + 32
        image, draw = self._canvas(height)
        self._header(draw, profile.name, "PVP")

        x0, y0, x1 = 34, 104, 686
        self._round(draw, (x0, y0, x1, y0 + panel_height), self.colors["panel"])
        y = y0 + 24
        for label, value in title_lines:
            draw.text((x0 + 28, y), f"{label}", font=self.font_label, fill=self.colors["accent"])
            draw.text((x0 + 94, y - 2), value, font=self.font_body, fill=self.colors["text"])
            y += 38
        if note_lines:
            y += 4
            draw.line((x0 + 28, y, x1 - 28, y), fill=self.colors["line"], width=1)
            y += 14
            for line in note_lines:
                draw.text((x0 + 28, y), line, font=self.font_small, fill=self.colors["muted"])
                y += 26
        return image

    def _render_egg(self, profile: PetProfile) -> Image.Image:
        stage_blocks = [self._stage_block_size(stage) for stage in profile.stages]
        chain_lines = list(self._wrap(" > ".join(profile.evolution_chain), 31)) if profile.evolution_chain else []
        chain_height = 28 + len(chain_lines) * 26 if chain_lines else 0
        content_height = chain_height + sum(stage_blocks) + max(0, len(stage_blocks) - 1) * 12
        height = 116 + content_height + 30
        image, draw = self._canvas(height)
        self._header(draw, profile.name, "蛋组与体型")

        y = 100
        if chain_lines:
            draw.text((38, y), "进化链", font=self.font_tiny, fill=self.colors["accent"])
            y += 24
            for line in chain_lines:
                draw.text((38, y), line, font=self.font_small, fill=self.colors["accent_2"])
                y += 26
            y += 4

        for stage, block_height in zip(profile.stages, stage_blocks):
            self._stage_block(draw, stage, y, block_height)
            y += block_height + 12
        return image

    def _stage_block_size(self, stage: StageBody) -> int:
        detail_lines = self._stage_detail_lines(stage)
        return 58 + len(detail_lines) * 27 + 18

    def _stage_detail_lines(self, stage: StageBody) -> list[str]:
        return [
            f"蛋组  {stage.egg_group}",
            f"身高  {stage.height_range}    体重  {stage.weight_range}",
            f"大块头  {stage.big_body_range}    小不点  {stage.small_body_range}",
        ]

    def _stage_block(self, draw: ImageDraw.ImageDraw, stage: StageBody, y: int, height: int) -> None:
        x0, x1 = 34, 686
        fill = self.colors["panel_alt"] if stage.is_egg else self.colors["panel"]
        self._round(draw, (x0, y, x1, y + height), fill)
        name = stage.name
        tag = "蛋" if stage.is_egg else "形态"
        draw.text((x0 + 24, y + 18), name, font=self.font_label, fill=self.colors["text"])
        tag_w = self._text_width(draw, tag, self.font_tiny) + 28
        draw.rounded_rectangle((x1 - tag_w - 22, y + 18, x1 - 22, y + 44), radius=8, fill="#273833")
        draw.text((x1 - tag_w - 8, y + 22), tag, font=self.font_tiny, fill=self.colors["accent_2"])

        line_y = y + 58
        for line in self._stage_detail_lines(stage):
            draw.text((x0 + 24, line_y), line, font=self.font_small, fill=self.colors["muted"])
            line_y += 27

    def _canvas(self, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        image = Image.new("RGB", (720, height), self.colors["bg"])
        return image, ImageDraw.Draw(image)

    def _header(self, draw: ImageDraw.ImageDraw, name: str, label: str) -> None:
        draw.rectangle((0, 0, 720, 76), fill=self.colors["header"])
        draw.rectangle((0, 76, 720, 80), fill=self.colors["accent"])
        draw.text((34, 23), f"查询 · {name}", font=self.font_title, fill=self.colors["text"])
        label_w = self._text_width(draw, label, self.font_small)
        draw.text((686 - label_w, 28), label, font=self.font_small, fill=self.colors["muted"])

    def _round(self, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str) -> None:
        draw.rounded_rectangle(box, radius=12, fill=fill, outline=self.colors["border"], width=1)

    def _wrap(self, text: str, width: int) -> Iterable[str]:
        return textwrap.wrap(text, width=width, replace_whitespace=False) or []

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]

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
