import unittest

from rockbot.parser import HELP_TEXT, CommandParser


class CommandParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_help_when_only_mentioned(self) -> None:
        command = self.parser.parse("@友哈巴赫")
        self.assertTrue(command.mentioned)
        self.assertTrue(command.help_requested)

    def test_parse_plain_query(self) -> None:
        command = self.parser.parse("查询 奇丽草")
        self.assertEqual(command.pet_name, "奇丽草")
        self.assertEqual(command.query, "body")

    def test_parse_breeding_query(self) -> None:
        command = self.parser.parse("配种 果冻")
        self.assertEqual(command.pet_name, "果冻")
        self.assertEqual(command.query, "breeding")

    def test_parse_mentioned_query(self) -> None:
        command = self.parser.parse("@友哈巴赫 查询 水蓝蓝")
        self.assertEqual(command.pet_name, "水蓝蓝")
        self.assertEqual(command.query, "body")

    def test_invalid_format(self) -> None:
        command = self.parser.parse("@友哈巴赫 水蓝蓝")
        self.assertEqual(command.error, HELP_TEXT)

    def test_ignore_unmentioned_message(self) -> None:
        command = self.parser.parse("奇丽草")
        self.assertFalse(command.mentioned)


if __name__ == "__main__":
    unittest.main()
