import unittest

from rockbot.parser import HELP_TEXT, CommandParser


class CommandParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_help_when_only_mentioned(self) -> None:
        command = self.parser.parse("@友哈巴赫")
        self.assertTrue(command.mentioned)
        self.assertTrue(command.help_requested)

    def test_parse_pvp(self) -> None:
        command = self.parser.parse("@友哈巴赫 奇丽草 pvp")
        self.assertEqual(command.pet_name, "奇丽草")
        self.assertEqual(command.query, "pvp")

    def test_parse_pvp_case_insensitive(self) -> None:
        command = self.parser.parse("@友哈巴赫 水蓝蓝 PVP")
        self.assertEqual(command.pet_name, "水蓝蓝")
        self.assertEqual(command.query, "pvp")

    def test_parse_egg(self) -> None:
        command = self.parser.parse("@友哈巴赫 奇丽草 查蛋")
        self.assertEqual(command.pet_name, "奇丽草")
        self.assertEqual(command.query, "egg")

    def test_invalid_format(self) -> None:
        command = self.parser.parse("@友哈巴赫 奇丽草")
        self.assertEqual(command.error, HELP_TEXT)

    def test_ignore_unmentioned_message(self) -> None:
        command = self.parser.parse("奇丽草 查蛋")
        self.assertFalse(command.mentioned)


if __name__ == "__main__":
    unittest.main()
