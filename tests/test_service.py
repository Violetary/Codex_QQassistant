import os
import tempfile
import unittest
from pathlib import Path

from rockbot.cache import JsonCache
from rockbot.render import CardRenderer
from rockbot.service import BotService


class BotServiceTest(unittest.TestCase):
    def test_help_reply(self) -> None:
        service = BotService()
        reply = service.handle_message("@友哈巴赫")
        self.assertIsNotNone(reply)
        self.assertIn("请按格式输入", reply.text)

    def test_generates_image_for_sample_pet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BotService(
                cache=JsonCache(Path(tmpdir) / "cache"),
                renderer=CardRenderer(Path(tmpdir) / "outputs"),
            )
            reply = service.handle_message("查询 奇丽草")
            self.assertTrue(reply.ok)
            self.assertIsNotNone(reply.image_path)
            self.assertTrue(os.path.exists(reply.image_path))

    def test_stage_alias_returns_family_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BotService(
                cache=JsonCache(Path(tmpdir) / "cache"),
                renderer=CardRenderer(Path(tmpdir) / "outputs"),
            )
            reply = service.handle_message("查询 波波拉")
            self.assertTrue(reply.ok)
            self.assertEqual("", reply.text)
            self.assertIsNotNone(reply.image_path)
            profile = service._get_profile("波波拉")
            self.assertEqual("水蓝蓝", profile.name)
            self.assertTrue(any(stage.is_egg for stage in profile.stages))

    def test_nonexistent_short_name_does_not_guess_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BotService(
                cache=JsonCache(Path(tmpdir) / "cache"),
                renderer=CardRenderer(Path(tmpdir) / "outputs"),
            )
            lion = service.handle_message("查询 狮鹫")
            self.assertFalse(lion.ok)
            self.assertIn("没有查到", lion.text)
            self.assertIsNone(lion.image_path)

    def test_real_griffin_names_return_family_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BotService(
                cache=JsonCache(Path(tmpdir) / "cache"),
                renderer=CardRenderer(Path(tmpdir) / "outputs"),
            )
            for name in ("小狮鹫", "皇家狮鹫", "神圣狮鹫"):
                with self.subTest(name=name):
                    reply = service.handle_message(f"查询 {name}")
                    self.assertTrue(reply.ok)
                    self.assertEqual("", reply.text)
                    self.assertIsNotNone(reply.image_path)

    def test_snow_doll_returns_image_and_old_format_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BotService(
                cache=JsonCache(Path(tmpdir) / "cache"),
                renderer=CardRenderer(Path(tmpdir) / "outputs"),
            )
            snow = service.handle_message("查询 雪影娃娃")
            self.assertTrue(snow.ok)
            self.assertEqual("", snow.text)
            self.assertIsNotNone(snow.image_path)

            old_format = service.handle_message("@友哈巴赫 水蓝蓝")
            self.assertFalse(old_format.ok)
            self.assertIn("请按格式输入", old_format.text)


if __name__ == "__main__":
    unittest.main()
