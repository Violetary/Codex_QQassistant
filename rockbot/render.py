from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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
    version = "v12"

    def __init__(self, output_dir: str | Path = "outputs/cards") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = 620
        self.margin_x = 34
        self.right_x = self.width - self.margin_x
        self.font_stage = self._font(24, bold=True)
        self.font_label = self._font(16, bold=True)
        self.font_body = self._font(20, bold=True)
        self.font_egg_group = self._font(18, bold=True)
        self.font_small = self._font(16, bold=True)
        self.font_tiny = self._font(14, bold=True)
        self.ornament_path = Path("assets/miku_table_milk_tea_blended.png")
        self.colors = {
            "bg": "#edf3f5",
            "accent": "#e5a936",
            "accent_2": "#0ea5a4",
            "text": "#15333c",
            "muted": "#607782",
            "line": "#cbdde1",
            "tag_bg": "#d9f1ee",
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
        egg_groups = [group for group in stage_groups if group.representative.is_egg]
        form_groups = [group for group in stage_groups if not group.representative.is_egg]
        ordered_groups = egg_groups + form_groups
        stage_blocks = [self._stage_group_block_size(group) for group in ordered_groups]
        chain_lines = self._chain_lines(profile)
        chain_height = self._chain_block_size(chain_lines)
        content_height = sum(stage_blocks) + max(0, len(stage_blocks) - 1) * 8
        height = 20 + content_height + chain_height + 18
        image, draw = self._canvas(height)
        self._draw_background_ornament(image)

        y = 20
        chain_rendered = False
        for index, (group, block_height) in enumerate(zip(ordered_groups, stage_blocks)):
            y = self._stage_group_block(draw, group, y, block_height, divider=index > 0)
            if group.representative.is_egg and chain_lines:
                y = self._render_chain(draw, chain_lines, y)
                chain_rendered = True
        if chain_lines and not chain_rendered:
            y = self._render_chain(draw, chain_lines, y)
        return image.crop((0, 0, self.width, max(1, y + 10)))

    def _chain_lines(self, profile: PetProfile) -> list[str]:
        chain = " > ".join(profile.evolution_chain)
        return self._wrap_pixels(chain, self.font_small, self.width - 68) if chain else []

    def _chain_block_size(self, chain_lines: list[str]) -> int:
        if not chain_lines:
            return 0
        return 58 + 22 * max(0, len(chain_lines) - 1)

    def _render_chain(self, draw: ImageDraw.ImageDraw, chain_lines: list[str], y: int) -> int:
        draw.text((self.margin_x, y), "进化链", font=self.font_tiny, fill=self.colors["accent"])
        line_y = y + 24
        for line in chain_lines:
            draw.text((self.margin_x, line_y), line, font=self.font_small, fill=self.colors["accent_2"])
            line_y += 22
        return y + self._chain_block_size(chain_lines)

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
        title_lines = self._stage_title_lines(group, tag_width=self._stage_tag_width(group))
        return 28 + 29 * len(title_lines) + 82

    def _stage_group_block(self, draw: ImageDraw.ImageDraw, group: StageDisplayGroup, y: int, height: int, divider: bool = True) -> int:
        stage = group.representative
        if divider:
            draw.line((self.margin_x, y - 9, self.right_x, y - 9), fill=self.colors["line"], width=1)

        tag = self._stage_tag(group)
        tag_w = self._text_width(draw, tag, self.font_tiny) + 24
        title_lines = self._stage_title_lines(group, tag_width=tag_w)
        draw.rounded_rectangle((self.right_x - tag_w, y + 1, self.right_x, y + 26), radius=8, fill=self.colors["tag_bg"])
        draw.text((self.right_x - tag_w + 12, y + 4), tag, font=self.font_tiny, fill=self.colors["accent_2"])

        title_y = y
        for line in title_lines:
            draw.text((self.margin_x, title_y), line, font=self.font_stage, fill=self.colors["text"])
            title_y += 29

        detail_y = y + 39 + 29 * (len(title_lines) - 1)
        left_label = self.margin_x
        left_value = self.margin_x + 52
        right_label = self.margin_x + 194
        right_value = self.margin_x + 246

        egg_bottom = detail_y + 19
        self._draw_bottom(draw, left_label, egg_bottom, "蛋组", self.font_label, self.colors["muted"])
        self._draw_pill(draw, left_value, egg_bottom, self._display_egg_group(stage.egg_group), self.font_egg_group)

        row1_bottom = detail_y + 50
        row2_bottom = detail_y + 81
        self._draw_bottom(draw, left_label, row1_bottom, "身高", self.font_label, self.colors["muted"])
        self._draw_bottom(draw, left_value, row1_bottom, self._format_measure(stage.height_range), self.font_body, self.colors["text"])
        self._draw_bottom(draw, right_label, row1_bottom, "体重", self.font_label, self.colors["muted"])
        self._draw_bottom(draw, right_value, row1_bottom, self._format_measure(stage.weight_range), self.font_body, self.colors["text"])

        self._draw_bottom(draw, left_label, row2_bottom, "大块头", self.font_label, self.colors["muted"])
        self._draw_bottom(draw, left_label + 64, row2_bottom, self._format_measure(stage.big_body_range), self.font_body, self.colors["text"])
        self._draw_bottom(draw, right_label, row2_bottom, "小不点", self.font_label, self.colors["muted"])
        self._draw_bottom(draw, right_label + 64, row2_bottom, self._format_measure(stage.small_body_range), self.font_body, self.colors["text"])
        return y + height + 8

    def _stage_tag(self, group: StageDisplayGroup) -> str:
        stage = group.representative
        if stage.is_egg:
            return "蛋"
        if self._is_lord_group(group):
            return "首领形态"
        return "形态"

    def _is_lord_group(self, group: StageDisplayGroup) -> bool:
        title = self._stage_group_title(group)
        return "首领" in title or "领主" in title or any("首领" in stage.name or "领主" in stage.name for stage in group.stages)

    def _stage_tag_width(self, group: StageDisplayGroup) -> int:
        return self._measure_text(self._stage_tag(group), self.font_tiny) + 24

    def _stage_title_lines(self, group: StageDisplayGroup, tag_width: int = 0) -> list[str]:
        title = self._stage_group_title(group)
        full_width = self.width - 112
        first_width = max(120, full_width - tag_width - 16)
        return self._wrap_pixels_with_first_width(title, self.font_stage, first_width, full_width)

    def _display_egg_group(self, egg_group: str) -> str:
        parts = re.split(r"[、,，/]+", egg_group or "")
        cleaned = [re.sub(r"组$", "", part.strip()) for part in parts if part.strip()]
        return "、".join(cleaned) or "未知"

    def _format_measure(self, value: str) -> str:
        return re.sub(r"\d+(?:\.\d+)?", lambda match: self._format_decimal(match.group(0)), str(value))

    def _format_decimal(self, value: str) -> str:
        try:
            number = Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return value
        if number == 0:
            return "0"
        return format(number.normalize(), "f")

    def _draw_bottom(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        bottom: int,
        text: str,
        font: ImageFont.ImageFont,
        fill: str,
    ) -> None:
        box = draw.textbbox((0, 0), text, font=font)
        draw.text((x, bottom - box[3]), text, font=font, fill=fill)

    def _draw_pill(self, draw: ImageDraw.ImageDraw, x: int, bottom: int, text: str, font: ImageFont.ImageFont) -> None:
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        height = box[3] - box[1]
        rect = (x - 8, bottom - height - 5, x + width + 10, bottom + 4)
        draw.rounded_rectangle(rect, radius=8, fill=self.colors["tag_bg"])
        self._draw_bottom(draw, x, bottom, text, font, self.colors["accent_2"])

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
        image = Image.new("RGB", (self.width, height), self.colors["bg"])
        return image, ImageDraw.Draw(image)

    def _draw_background_ornament(self, image: Image.Image) -> None:
        if not self.ornament_path.exists():
            return
        try:
            ornament = Image.open(self.ornament_path).convert("RGBA")
        except OSError:
            return
        max_width = 178
        max_height = 178
        scale = min(max_width / ornament.width, max_height / ornament.height)
        if scale <= 0:
            return
        size = (max(1, int(ornament.width * scale)), max(1, int(ornament.height * scale)))
        ornament = ornament.resize(size, Image.Resampling.LANCZOS)
        ornament.putalpha(ornament.getchannel("A").point(lambda alpha: int(alpha * 0.72)))
        layer = image.convert("RGBA")
        layer.alpha_composite(ornament, (self.width - ornament.width + 7, image.height - ornament.height + 7))
        image.paste(layer.convert("RGB"))

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

    def _wrap_pixels_with_first_width(
        self,
        text: str,
        font: ImageFont.ImageFont,
        first_width: int,
        max_width: int,
    ) -> list[str]:
        if not text:
            return []
        lines: list[str] = []
        current = ""
        for char in text:
            candidate = current + char
            limit = first_width if not lines else max_width
            if current and self._measure_text(candidate, font) > limit and char not in "）)]}":
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
        if bold:
            candidates = [
                "C:/Windows/Fonts/msyhbd.ttc",
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/NotoSansSC-VF.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
            ]
        else:
            candidates = [
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/NotoSansSC-VF.ttf",
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/simsun.ttc",
            ]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()
