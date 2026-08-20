import json
import unittest
from pathlib import Path


class DataIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = json.loads(Path("data/pets.seed.json").read_text(encoding="utf-8"))

    def test_form_and_egg_counts(self) -> None:
        stages = [stage for family in self.db["pets"] for stage in family["stages"]]
        forms = [stage for stage in stages if not stage.get("is_egg")]
        eggs = [stage for stage in stages if stage.get("is_egg")]
        self.assertEqual(442, len(forms))
        self.assertEqual(self.db["meta"]["family_count"], len(eggs))

    def test_body_fields_are_complete(self) -> None:
        missing = []
        for family in self.db["pets"]:
            for stage in family["stages"]:
                for key in ("height_range", "weight_range", "big_body_range", "small_body_range"):
                    if stage.get(key) in ("", "未知", None):
                        missing.append((family["name"], stage["name"], key))
        self.assertEqual([], missing)

    def test_water_blue_egg_and_form_weights_are_separate(self) -> None:
        family = next(family for family in self.db["pets"] if "水蓝蓝" in family["aliases"])
        stages = {stage["name"]: stage for stage in family["stages"]}
        self.assertEqual("1.3528", stages["水蓝蓝蛋"]["big_body_range"])
        self.assertEqual("4.1828", stages["水蓝蓝"]["big_body_range"])


if __name__ == "__main__":
    unittest.main()
