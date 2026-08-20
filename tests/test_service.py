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
            reply = service.handle_message("@友哈巴赫 奇丽草 查蛋")
            self.assertTrue(reply.ok)
            self.assertIsNotNone(reply.image_path)
            self.assertTrue(os.path.exists(reply.image_path))

    def test_stage_alias_returns_family_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BotService(
                cache=JsonCache(Path(tmpdir) / "cache"),
                renderer=CardRenderer(Path(tmpdir) / "outputs"),
            )
            reply = service.handle_message("@友哈巴赫 波波拉 查蛋")
            self.assertTrue(reply.ok)
            self.assertIn("水蓝蓝", reply.text)
            self.assertIsNotNone(reply.image_path)


if __name__ == "__main__":
    unittest.main()
