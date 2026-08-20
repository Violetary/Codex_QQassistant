import tempfile
import unittest
from pathlib import Path

from rockbot.render import CardRenderer
from rockbot.sources import LocalJsonSource


class CardRendererTest(unittest.TestCase):
    def test_groups_identical_body_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = LocalJsonSource().fetch("蹦蹦花")
            renderer = CardRenderer(Path(tmpdir))
            groups = renderer._group_stages(profile.stages)
            titles = [renderer._stage_group_title(group) for group in groups]

            self.assertLess(len(groups), len(profile.stages))
            self.assertIn("蹦蹦花（海神球、彩玉球、短毛球、象牙球）", titles)
            self.assertIn("蹦蹦种子（原始、海神球、彩玉球、短毛球、象牙球）", titles)

    def test_grouped_body_card_renders_v13_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = LocalJsonSource().fetch("蹦蹦花")
            renderer = CardRenderer(Path(tmpdir))
            image_path = renderer.render(profile, "body", force=True)

            self.assertEqual("63_body_v13.png", image_path.name)
            self.assertTrue(image_path.exists())

    def test_breeding_card_renders_on_demand(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = LocalJsonSource().fetch("果冻")
            renderer = CardRenderer(Path(tmpdir))
            image_path = renderer.render(profile, "breeding", force=True)

            self.assertEqual("313_breeding_v3.png", image_path.name)
            self.assertTrue(image_path.exists())

    def test_breeding_groups_merge_order_only_changes(self) -> None:
        profile = LocalJsonSource().fetch("梦悠悠")
        renderer = CardRenderer()
        top_cards = renderer._breeding_top_cards(profile)

        self.assertEqual(1, len(top_cards))
        self.assertEqual(["魔力", "妖精"], top_cards[0].groups)
        self.assertEqual("梦悠悠", top_cards[0].name)

    def test_breeding_groups_show_distinct_group_sets(self) -> None:
        profile = LocalJsonSource().fetch("果冻")
        renderer = CardRenderer()
        top_cards = renderer._breeding_top_cards(profile)

        self.assertEqual(2, len(top_cards))
        self.assertEqual("果冻", top_cards[0].name)
        self.assertEqual(["海洋", "魔力"], top_cards[0].groups)
        self.assertEqual("椰浆布丁、熔岩布丁", top_cards[1].name)
        self.assertEqual(["海洋"], top_cards[1].groups)


if __name__ == "__main__":
    unittest.main()
