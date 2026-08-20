from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import PetProfile, QueryKind, StageBody


@dataclass(slots=True)
class StageDisplayGroup:
    stages: list[StageBody]

    @property
    def representative(self) -> StageBody:
        return self.stages[0]


class CardRenderer:
    version = "v6"

    def __init__(self, output_dir: str | Path = "outputs/cards") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_title = self._font(32, bold=True)
        self.font_label = self._font(21, bold=True)
        self.font_body = self._font(23)
        self.font_small = self._font(18)
        self.font_tiny = self._font(16)
        self.colors = {
            "bg": "#f5fbff",
            "header": "#087f8c",
            "panel": "#ffffff",
            "panel_alt": "#eefbff",
            "border": "#20d6c7",
            "accent": "#f4b63f",
            "accent_2": "#0ea5a4",
            "text": "#14313a",
            "muted": "#5f7480",
            "subtle": "#8aa0aa",
            "line": "#d5edf0",
            "tag_bg": "#dff8f5",
        }

    def render(self, profile: PetProfile, query: QueryKind, force: bool = False) -> Path:
        output = self.output_path(profile, query)
        if output.exists() and not force:
            return output

        image = self._render_body(profile)
        image.save(output, optimize=True)
        return output

    def output_path(self, profile: PetProfile, query: QueryKind) -> Path:
        prefix = str(profile.family_id) if profile.family_id is not None else profile.name
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", prefix).strip() or "pet"
        return self.output_dir / f"{safe_name}_{query}_{self.version}.png"

    def _render_body(self, profile: PetProfile) -> Image.Image:
        stage_groups = self._group_stages(profile.stages)
        stage_blocks = [self._stage_group_block_size(group) for group in stage_groups]
        chain_lines = self._chain_lines(profile)
        chain_height = 84 if chain_lines else 0
        content_height = sum(stage_blocks) + max(0, len(stage_blocks) - 1) * 12
        height = 94 + chain_height + content_height + 24
        image, draw = self._canvas(height)
        self._header(draw, profile.name)

        y = 94
        if chain_lines:
            y = self._render_chain(draw, chain_lines, y)

        for group, block_height in zip(stage_groups, stage_blocks):
            self._stage_group_block(draw, group, y, block_height)
            y += block_height + 12
        return image

    def _chain_lines(self, profile: PetProfile) -> list[str]:
        chain = " > ".join(profile.evolution_chain)
        return self._wrap_pixels(chain, self.font_small, 650) if chain else []

    def _render_chain(self, draw: ImageDraw.ImageDraw, chain_lines: list[str], y: int) -> int:
        draw.text((34, y + 10), "进化链", font=self.font_tiny, fill=self.colors["accent"])
        line_y = y + 36
        for line in chain_lines:
            draw.text((34, line_y), line, font=self.font_small, fill=self.colors["accent_2"])
            line_y += 25
        return line_y + 15

    def _group_stages(self, stages: list[StageBody]) -> list[StageDisplayGroup]:
        groups: list[StageDisplayGroup] = []
        by_key: dict[tuple[str, ...], StageDisplayGroup] = {}
        for stage in stages:
            key = self._stage_group_key(stage)
            group = by_key.get(key)
            if group is None:
                group = StageDisplayGroup([stage])
                by_key[key] = group
                groups.append(group)
            else:
                group.stages.append(stage)
        return groups

    def _stage_group_key(self, stage: StageBody) -> tuple[str, ...]:
        return (
            "egg" if stage.is_egg else "form",
            stage.egg_group,
            stage.height_range,
            stage.weight_range,
            stage.big_body_range,
            stage.small_body_range,
        )

    def _stage_group_block_size(self, group: StageDisplayGroup) -> int:
        title_lines = self._stage_title_lines(group)
        return 18 + len(title_lines) * 28 + 16 + 70 + 18

    def _stage_group_block(self, draw: ImageDraw.ImageDraw, group: StageDisplayGroup, y: int, height: int) -> None:
        stage = group.representative
        x0, x1 = 34, 686
        fill = self.colors["panel_alt"] if stage.is_egg else self.colors["panel"]
        self._round(draw, (x0, y, x1, y + height), fill)
        title_lines = self._stage_title_lines(group)
        tag = "蛋" if stage.is_egg else "形态"
        if len(group.stages) > 1 and not stage.is_egg:
            tag = f"形态×{len(group.stages)}"
        tag_w = self._text_width(draw, tag, self.font_tiny) + 28
        draw.rounded_rectangle((x1 - tag_w - 20, y + 18, x1 - 20, y + 44), radius=8, fill=self.colors["tag_bg"])
        draw.text((x1 - tag_w - 6, y + 22), tag, font=self.font_tiny, fill=self.colors["accent_2"])

        title_y = y + 18
        for line in title_lines:
            draw.text((x0 + 24, title_y), line, font=self.font_label, fill=self.colors["text"])
            title_y += 28

        detail_y = y + 18 + len(title_lines) * 28 + 16
        for line_x in (242, 462):
            draw.line((line_x, detail_y + 2, line_x, y + height - 18), fill=self.colors["line"], width=1)

        draw.text((58, detail_y + 1), "蛋组", font=self.font_tiny, fill=self.colors["muted"])
        draw.text((58, detail_y + 31), self._display_egg_group(stage.egg_group), font=self.font_body, fill=self.colors["accent_2"])

        middle_rows = [("身高", stage.height_range), ("体重", stage.weight_range)]
        right_rows = [("大块头", stage.big_body_range), ("小不点", stage.small_body_range)]
        for row_index, (label, value) in enumerate(middle_rows):
            row_y = detail_y + row_index * 33
            draw.text((272, row_y), label, font=self.font_tiny, fill=self.colors["muted"])
            draw.text((322, row_y - 3), value, font=self.font_body, fill=self.colors["text"])
        for row_index, (label, value) in enumerate(right_rows):
            row_y = detail_y + row_index * 33
            draw.text((486, row_y), label, font=self.font_tiny, fill=self.colors["muted"])
            draw.text((552, row_y - 3), value, font=self.font_body, fill=self.colors["text"])

    def _stage_title_lines(self, group: StageDisplayGroup) -> list[str]:
        title = self._stage_group_title(group)
        return self._wrap_pixels(title, self.font_label, 520)

    def _display_egg_group(self, egg_group: str) -> str:
        parts = re.split(r"[、,，/]+", egg_group or "")
        cleaned = [re.sub(r"组$", "", part.strip()) for part in parts if part.strip()]
        return "、".join(cleaned) or "未知"

    def _stage_group_title(self, group: StageDisplayGroup) -> str:
        names = [stage.name for stage in group.stages]
        if len(names) == 1:
            return names[0]

        variants = [self._split_variant_name(name) for name in names]
        bases = {base for base, _variant in variants if base}
        if len(bases) == 1:
            base = next(iter(bases))
            variant_names = [self._clean_variant(variant) if variant else "原始" for _base, variant in variants]
            return f"{base}（{'、'.join(variant_names)}）"
        return "、".join(names)

    def _split_variant_name(self, name: str) -> tuple[str, str]:
        match = re.match(r"^(.+?)（(.+)）$", name)
        if not match:
            return name, ""
        return match.group(1), match.group(2)

    def _clean_variant(self, variant: str) -> str:
        return re.sub(r"(形态|的样子)$", "", variant)

    def _canvas(self, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        image = Image.new("RGB", (720, height), self.colors["bg"])
        return image, ImageDraw.Draw(image)

    def _header(self, draw: ImageDraw.ImageDraw, name: str) -> None:
        draw.rectangle((0, 0, 720, 76), fill=self.colors["header"])
        draw.rectangle((0, 76, 720, 80), fill=self.colors["accent"])
        draw.text((34, 23), f"查询 · {name}", font=self.font_title, fill="#ffffff")

    def _round(self, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str) -> None:
        draw.rounded_rectangle(box, radius=8, fill=fill, outline=self.colors["border"], width=1)

    def _wrap_pixels(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
        if not text:
            return []
        lines: list[str] = []
        current = ""
        for char in text:
            candidate = current + char
            if current and self._measure_text(candidate, font) > max_width and char not in "）)]}":
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]

    def _measure_text(self, text: str, font: ImageFont.ImageFont) -> int:
        image = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(image)
        return self._text_width(draw, text, font)

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
