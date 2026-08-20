from __future__ import annotations

import json
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


@dataclass(slots=True)
class BreedingTopCard:
    name: str
    groups: list[str]
    stage: StageBody | None


class CardRenderer:
    version = "v13"
    breeding_version = "v3"

    def __init__(self, output_dir: str | Path = "outputs/cards", database_path: str | Path = "data/pets.seed.json") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = Path(database_path)
        self._breeding_profiles: list[PetProfile] | None = None
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
        self.portrait_dir = Path("data/raw/roco_egg_master/高清精灵头像")
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

        image = self._render_breeding(profile) if query == "breeding" else self._render_body(profile)
        image.save(output, optimize=True)
        return output

    def output_path(self, profile: PetProfile, query: QueryKind) -> Path:
        prefix = str(profile.family_id) if profile.family_id is not None else profile.name
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", prefix).strip() or "pet"
        if query == "breeding":
            return self.output_dir / f"{safe_name}_breeding_{self.breeding_version}.png"
        return self.output_dir / f"{safe_name}_{query}_{self.version}.png"

    def can_breed(self, profile: PetProfile) -> bool:
        return bool(self._breeding_group_sets(profile))

    def _render_breeding(self, profile: PetProfile) -> Image.Image:
        top_cards = self._breeding_top_cards(profile)
        if not top_cards:
            raise ValueError(f"{profile.name} cannot breed")

        query_groups: list[str] = []
        seen_groups: set[str] = set()
        for card in top_cards:
            for group in card.groups:
                if group not in seen_groups:
                    seen_groups.add(group)
                    query_groups.append(group)

        sections = [(group, self._breeding_names_for_group(group)) for group in query_groups]
        width = 790
        margin_x = 34
        column_gap = 18
        columns = 4
        column_width = (width - margin_x * 2 - column_gap * (columns - 1)) // columns
        row_height = 30
        header_height = 112 + 76 * max(0, (len(top_cards) - 1) // 2)
        section_gap = 20
        section_heights = [
            44 + ((len(names) + columns - 1) // columns) * row_height + 8 for _group, names in sections
        ]
        height = header_height + sum(section_heights) + section_gap * max(0, len(section_heights) - 1) + 18

        image = Image.new("RGB", (width, height), self.colors["bg"])
        draw = ImageDraw.Draw(image)
        self._draw_breeding_portrait(image, top_cards[0].stage, width)
        draw = ImageDraw.Draw(image)

        self._draw_breeding_header(draw, top_cards, width, header_height)
        draw.line((margin_x, header_height - 6, width - margin_x, header_height - 6), fill=self.colors["line"], width=1)

        y = header_height + 14
        for index, (group, names) in enumerate(sections):
            tag_right, _tag_bottom = self._draw_breeding_pill(draw, margin_x, y - 2, group, self.font_egg_group, pad_x=13, pad_y=6)
            draw.text((tag_right + 12, y + 4), f"{len(names)}只", font=self.font_tiny, fill=self.colors["muted"])
            names_y = y + 42
            for item_index, name in enumerate(names):
                column = item_index % columns
                row = item_index // columns
                x = margin_x + column * (column_width + column_gap)
                item_y = names_y + row * row_height
                font = self.font_body if self._measure_text(name, self.font_body) <= column_width else self._font(18, bold=True)
                draw.text((x, item_y), self._ellipsize(name, font, column_width), font=font, fill=self.colors["text"])
            y += section_heights[index] + section_gap

        return image

    def _draw_breeding_header(
        self,
        draw: ImageDraw.ImageDraw,
        top_cards: list[BreedingTopCard],
        width: int,
        header_height: int,
    ) -> None:
        block_specs = [(34, 24, 220), (292, 24, 300)]
        for index, card in enumerate(top_cards):
            if index < len(block_specs):
                x, y, block_width = block_specs[index]
            else:
                x = 34 + (index % 2) * 258
                y = 24 + (index // 2) * 76
                block_width = 300

            title_font = self._font(32, bold=True) if index == 0 else self._font(21, bold=True)
            title = self._ellipsize(card.name, title_font, block_width)
            draw.text((x, y), title, font=title_font, fill=self.colors["text"])

            label_x = x
            row_bottom = y + 68
            self._draw_bottom(draw, label_x, row_bottom, "蛋组", self.font_small, self.colors["muted"])
            pill_x = label_x + 46
            for group in card.groups:
                if pill_x + self._measure_text(group, self.font_tiny) + 24 > x + block_width:
                    pill_x = label_x + 46
                    row_bottom += 28
                pill_x, _pill_bottom = self._draw_breeding_pill_bottom(draw, pill_x, row_bottom, group, self.font_tiny)
                pill_x += 7

    def _breeding_names_for_group(self, group: str) -> list[str]:
        items: list[tuple[int, str]] = []
        seen: set[tuple[int, str]] = set()
        for profile in self._all_breeding_profiles():
            if group not in self._profile_breeding_groups(profile):
                continue
            name = self._highest_breedable_name(profile)
            if not name:
                continue
            family_id = profile.family_id if profile.family_id is not None else 999999
            key = (family_id, name)
            if key in seen:
                continue
            seen.add(key)
            items.append(key)
        items.sort(key=lambda item: (item[0], item[1]))
        return [name for _family_id, name in items]

    def _all_breeding_profiles(self) -> list[PetProfile]:
        if self._breeding_profiles is not None:
            return self._breeding_profiles
        if not self.database_path.exists():
            self._breeding_profiles = []
            return self._breeding_profiles
        try:
            payload = json.loads(self.database_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._breeding_profiles = []
            return self._breeding_profiles
        records = payload.get("pets", payload)
        if not isinstance(records, list):
            self._breeding_profiles = []
            return self._breeding_profiles
        self._breeding_profiles = [PetProfile.from_dict(item) for item in records if isinstance(item, dict)]
        return self._breeding_profiles

    def _breeding_top_cards(self, profile: PetProfile) -> list[BreedingTopCard]:
        group_sets = self._breeding_group_sets(profile)
        cards: list[BreedingTopCard] = []
        for index, item in enumerate(group_sets):
            groups = item["groups"]
            stages = item["stages"]
            stage = stages[0] if stages else None
            if index == 0:
                name = self._highest_breedable_name(profile) or profile.name
            else:
                names: list[str] = []
                for stage_item in stages:
                    stage_name = self._clean_breeding_name(stage_item.name)
                    if stage_name and stage_name not in names:
                        names.append(stage_name)
                name = "、".join(names[:2])
                if len(names) > 2:
                    name += f"等{len(names)}种"
            cards.append(BreedingTopCard(name=name, groups=groups, stage=stage))
        return cards

    def _breeding_group_sets(self, profile: PetProfile) -> list[dict[str, list[StageBody] | list[str]]]:
        by_key: dict[tuple[str, ...], dict[str, list[StageBody] | list[str]]] = {}
        ordered_keys: list[tuple[str, ...]] = []
        for stage in profile.stages:
            if stage.is_egg:
                continue
            groups = self._stage_breeding_groups(stage)
            if not groups:
                continue
            key = tuple(sorted(groups))
            if key not in by_key:
                by_key[key] = {"groups": groups, "stages": []}
                ordered_keys.append(key)
            stages = by_key[key]["stages"]
            assert isinstance(stages, list)
            stages.append(stage)
        return [by_key[key] for key in ordered_keys]

    def _profile_breeding_groups(self, profile: PetProfile) -> list[str]:
        groups: list[str] = []
        seen: set[str] = set()
        for item in self._breeding_group_sets(profile):
            for group in item["groups"]:
                if isinstance(group, str) and group not in seen:
                    seen.add(group)
                    groups.append(group)
        return groups

    def _stage_breeding_groups(self, stage: StageBody) -> list[str]:
        groups = [group for group in self._split_egg_groups(stage.egg_group) if group != "无法孵蛋"]
        cleaned: list[str] = []
        seen: set[str] = set()
        for group in groups:
            if group and group not in seen:
                seen.add(group)
                cleaned.append(group)
        return cleaned

    def _split_egg_groups(self, egg_group: str) -> list[str]:
        parts = re.split(r"[、,，/]+", egg_group or "")
        return [re.sub(r"组$", "", part.strip()) for part in parts if part.strip()]

    def _highest_breedable_name(self, profile: PetProfile) -> str:
        breedable_stages = [stage for stage in profile.stages if not stage.is_egg and self._stage_breeding_groups(stage)]
        if not breedable_stages:
            return ""
        breedable_names = {self._clean_breeding_name(stage.name) for stage in breedable_stages}
        for chain_name in reversed(profile.evolution_chain):
            cleaned = self._clean_breeding_name(chain_name)
            if cleaned in breedable_names:
                return cleaned
        return self._clean_breeding_name(breedable_stages[-1].name)

    def _clean_breeding_name(self, name: str) -> str:
        return re.sub(r"[（(].*?[）)]$", "", name or "").strip()

    def _draw_breeding_pill(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.ImageFont,
        pad_x: int = 10,
        pad_y: int = 4,
    ) -> tuple[int, int]:
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        height = box[3] - box[1]
        rect = (x, y, x + width + pad_x * 2, y + height + pad_y * 2)
        draw.rounded_rectangle(rect, radius=8, fill=self.colors["tag_bg"])
        text_x = x + pad_x - box[0]
        text_y = y + (rect[3] - rect[1] - height) / 2 - box[1]
        draw.text((text_x, text_y), text, font=font, fill=self.colors["accent_2"])
        return rect[2], rect[3]

    def _draw_breeding_pill_bottom(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        bottom: int,
        text: str,
        font: ImageFont.ImageFont,
        pad_x: int = 10,
        pad_y: int = 4,
    ) -> tuple[int, int]:
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        height = box[3] - box[1]
        y = bottom - height - pad_y * 2
        rect = (x, y, x + width + pad_x * 2, bottom)
        draw.rounded_rectangle(rect, radius=8, fill=self.colors["tag_bg"])
        text_x = x + pad_x - box[0]
        text_y = y + (rect[3] - rect[1] - height) / 2 - box[1]
        draw.text((text_x, text_y), text, font=font, fill=self.colors["accent_2"])
        return rect[2], rect[3]

    def _draw_breeding_portrait(self, image: Image.Image, stage: StageBody | None, width: int) -> None:
        if stage is None:
            return
        portrait_path = self._portrait_path_for_stage(stage)
        if portrait_path is None:
            return
        try:
            portrait = Image.open(portrait_path).convert("RGBA")
        except OSError:
            return

        max_height = 112
        scale = max_height / portrait.height
        size = (max(1, int(portrait.width * scale)), max_height)
        portrait = portrait.resize(size, Image.Resampling.LANCZOS)
        portrait.putalpha(portrait.getchannel("A").point(lambda alpha: int(alpha * 0.20)))
        layer = image.convert("RGBA")
        layer.alpha_composite(portrait, (width - portrait.width - 16, 2))
        image.paste(layer.convert("RGB"))

    def _ellipsize(self, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        if self._measure_text(text, font) <= max_width:
            return text
        value = text
        while len(value) > 1 and self._measure_text(value + "…", font) > max_width:
            value = value[:-1]
        return value + "…"

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
        self._draw_top_right_portrait(image, ordered_groups, stage_blocks, chain_height, bool(chain_lines))

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

    def _draw_top_right_portrait(
        self,
        image: Image.Image,
        ordered_groups: list[StageDisplayGroup],
        stage_blocks: list[int],
        chain_height: int,
        has_chain: bool,
    ) -> None:
        if not ordered_groups or not stage_blocks:
            return
        portrait_path = self._first_stage_portrait_path(ordered_groups)
        if portrait_path is None:
            return
        try:
            portrait = Image.open(portrait_path).convert("RGBA")
        except OSError:
            return

        top_area_height = 20 + stage_blocks[0] + 8
        if ordered_groups[0].representative.is_egg and has_chain:
            top_area_height += chain_height
        top_area_height = max(96, top_area_height - 9)
        max_height = max(1, top_area_height - 6)
        scale = max_height / portrait.height
        size = (max(1, int(portrait.width * scale)), max_height)
        portrait = portrait.resize(size, Image.Resampling.LANCZOS)
        portrait.putalpha(portrait.getchannel("A").point(lambda alpha: int(alpha * 0.20)))

        layer = image.convert("RGBA")
        layer.alpha_composite(portrait, (self.width - portrait.width - 6, 2))
        image.paste(layer.convert("RGB"))

    def _first_stage_portrait_path(self, ordered_groups: list[StageDisplayGroup]) -> Path | None:
        for group in ordered_groups:
            for stage in group.stages:
                if stage.is_egg:
                    continue
                path = self._portrait_path_for_stage(stage)
                if path is not None:
                    return path
        return None

    def _portrait_path_for_stage(self, stage: StageBody) -> Path | None:
        candidates: list[Path] = []
        if stage.form_id is not None:
            candidates.append(self.portrait_dir / f"{stage.form_id}-{stage.name}.png")
        candidates.extend(self.portrait_dir.glob(f"*-{stage.name}.png"))
        for path in candidates:
            if path.exists():
                return path
        return None

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
