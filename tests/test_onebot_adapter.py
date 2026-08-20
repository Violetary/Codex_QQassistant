import tempfile
import unittest
from pathlib import Path

from rockbot.adapters.onebot import OneBotConfig, OneBotHTTPAdapter
from rockbot.cache import JsonCache
from rockbot.render import CardRenderer
from rockbot.service import BotService


class OneBotHTTPAdapterTest(unittest.TestCase):
    def make_adapter(self) -> OneBotHTTPAdapter:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        service = BotService(
            cache=JsonCache(Path(tmpdir.name) / "cache"),
            renderer=CardRenderer(Path(tmpdir.name) / "outputs"),
        )
        return OneBotHTTPAdapter(service, OneBotConfig(quick_reply=True))

    def test_group_at_segment_triggers_reply(self) -> None:
        adapter = self.make_adapter()
        result = adapter.handle_event(
            {
                "post_type": "message",
                "message_type": "group",
                "self_id": 10001,
                "group_id": 20002,
                "message": [
                    {"type": "at", "data": {"qq": "10001"}},
                    {"type": "text", "data": {"text": " 波波拉 pvp"}},
                ],
            }
        )
        self.assertIn("reply", result)
        self.assertEqual(result["reply"][0]["type"], "image")
        self.assertTrue(result["reply"][0]["data"]["file"].startswith("base64://"))

    def test_empty_event_falls_back_to_recent_contact(self) -> None:
        class FallbackAdapter(OneBotHTTPAdapter):
            def __init__(self, service):  # type: ignore[no-untyped-def]
                super().__init__(service)
                self.contacts = [
                    {
                        "msgId": "recent-1",
                        "msgTime": "100",
                        "lastestMsg": {
                            "self_id": 10001,
                            "user_id": 10002,
                            "message_type": "private",
                            "post_type": "message",
                            "raw_message": "@友哈巴赫 水蓝蓝 查蛋",
                            "message": [
                                {"type": "text", "data": {"text": "@友哈巴赫 水蓝蓝 查蛋"}}
                            ],
                        },
                    }
                ]

            def _call_api(self, action, payload):  # type: ignore[no-untyped-def]
                if action == "get_recent_contact":
                    return {
                        "status": "ok",
                        "retcode": 0,
                        "data": self.contacts,
                    }
                return {"status": "ok", "retcode": 0}

        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        service = BotService(
            cache=JsonCache(Path(tmpdir.name) / "cache"),
            renderer=CardRenderer(Path(tmpdir.name) / "outputs"),
        )
        adapter = FallbackAdapter(service)
        result = adapter.handle_event({})
        self.assertTrue(result["handled"])
        repeated = adapter.handle_event({})
        self.assertFalse(repeated["handled"])

    def test_recent_contact_seed_then_new_message(self) -> None:
        class PollAdapter(OneBotHTTPAdapter):
            def __init__(self, service):  # type: ignore[no-untyped-def]
                super().__init__(service)
                self.contacts = [
                    {
                        "msgId": "old",
                        "msgTime": "100",
                        "lastestMsg": {
                            "self_id": 10001,
                            "user_id": 10002,
                            "message_type": "private",
                            "post_type": "message",
                            "raw_message": "@友哈巴赫 魔力猫 查蛋",
                            "message": [{"type": "text", "data": {"text": "@友哈巴赫 魔力猫 查蛋"}}],
                        },
                    }
                ]
                self.sent = 0

            def _call_api(self, action, payload):  # type: ignore[no-untyped-def]
                if action == "get_recent_contact":
                    return {"status": "ok", "retcode": 0, "data": self.contacts}
                self.sent += 1
                return {"status": "ok", "retcode": 0}

        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        service = BotService(
            cache=JsonCache(Path(tmpdir.name) / "cache"),
            renderer=CardRenderer(Path(tmpdir.name) / "outputs"),
        )
        adapter = PollAdapter(service)
        adapter._seed_recent_contact_ids()
        adapter.contacts = [
            {
                "msgId": "new",
                "msgTime": "101",
                "lastestMsg": {
                    "self_id": 10001,
                    "user_id": 10002,
                    "message_type": "private",
                    "post_type": "message",
                    "raw_message": "@友哈巴赫 雪影娃娃 查蛋",
                    "message": [{"type": "text", "data": {"text": "@友哈巴赫 雪影娃娃 查蛋"}}],
                },
            }
        ]
        result = adapter._handle_recent_contact_once(send_reply=True)
        self.assertTrue(result["handled"])
        self.assertEqual(1, adapter.sent)

    def test_group_cq_at_triggers_reply(self) -> None:
        adapter = self.make_adapter()
        result = adapter.handle_event(
            {
                "post_type": "message",
                "message_type": "group",
                "self_id": 10001,
                "group_id": 20002,
                "raw_message": "[CQ:at,qq=10001] 水蓝蓝 查蛋",
                "message": "[CQ:at,qq=10001] 水蓝蓝 查蛋",
            }
        )
        self.assertIn("reply", result)

    def test_unmentioned_group_message_is_ignored(self) -> None:
        adapter = self.make_adapter()
        result = adapter.handle_event(
            {
                "post_type": "message",
                "message_type": "group",
                "self_id": 10001,
                "group_id": 20002,
                "raw_message": "水蓝蓝 查蛋",
                "message": [{"type": "text", "data": {"text": "水蓝蓝 查蛋"}}],
            }
        )
        self.assertFalse(result["handled"])

    def test_plain_at_prefix_triggers_reply(self) -> None:
        adapter = self.make_adapter()
        result = adapter.handle_event(
            {
                "post_type": "message",
                "message_type": "group",
                "self_id": 10001,
                "group_id": 20002,
                "raw_message": "@友哈巴赫 水蓝蓝 查蛋",
                "message": [{"type": "text", "data": {"text": "@友哈巴赫 水蓝蓝 查蛋"}}],
            }
        )
        self.assertIn("reply", result)

    def test_message_sent_self_event_triggers_reply(self) -> None:
        adapter = self.make_adapter()
        result = adapter.handle_event(
            {
                "post_type": "message_sent",
                "message_type": "private",
                "self_id": 10001,
                "user_id": 10002,
                "raw_message": "水蓝蓝 查蛋",
                "message": [{"type": "text", "data": {"text": "水蓝蓝 查蛋"}}],
            }
        )
        self.assertIn("reply", result)

    def test_camel_case_event_triggers_reply(self) -> None:
        adapter = self.make_adapter()
        result = adapter.handle_event(
            {
                "postType": "message",
                "messageType": "private",
                "selfId": 10001,
                "userId": 10002,
                "rawMessage": "@友哈巴赫 水蓝蓝 查蛋",
                "message": [{"type": "text", "data": {"text": "@友哈巴赫 水蓝蓝 查蛋"}}],
            }
        )
        self.assertIn("reply", result)


if __name__ == "__main__":
    unittest.main()
