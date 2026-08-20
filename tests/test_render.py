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

    def test_grouped_body_card_renders_v6_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = LocalJsonSource().fetch("蹦蹦花")
            renderer = CardRenderer(Path(tmpdir))
            image_path = renderer.render(profile, "body", force=True)

            self.assertEqual("63_body_v6.png", image_path.name)
            self.assertTrue(image_path.exists())


if __name__ == "__main__":
    unittest.main()
