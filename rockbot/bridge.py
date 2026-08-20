from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .adapters.onebot import OneBotConfig, OneBotHTTPAdapter
from .service import BotService


class BridgeHandler(BaseHTTPRequestHandler):
    service: BotService
    onebot: OneBotHTTPAdapter | None = None
    event_log_path = Path("logs/onebot-events.log")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/onebot":
            self._handle_onebot()
            return
        if self.path != "/message":
            self._send_json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        message = str(payload.get("raw_text", ""))
        reply = self.service.handle_message(message)
        if reply is None:
            self._send_json(200, {"ok": False, "triggered": False})
            return
        self._send_json(
            200,
            {
                "ok": reply.ok,
                "triggered": True,
                "text": reply.text,
                "image_path": reply.image_path,
            },
        )

    def _handle_onebot(self) -> None:
        if self.onebot is None:
            self._send_json(503, {"ok": False, "error": "onebot adapter is not enabled"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw_body or "{}")
            self._append_event_log(payload)
            if not isinstance(payload, dict):
                self._send_json(200, {"ok": True, "handled": False, "ignored": "non-object payload"})
                return
            result = self.onebot.handle_event(payload)
        except Exception as exc:  # Keep OneBot POST alive; log through JSON response.
            self._append_event_log({"error": str(exc), "raw_body": raw_body})
            self._send_json(200, {"ok": False, "error": str(exc)})
            return
        self._send_json(200, result)

    def _append_event_log(self, payload: Any) -> None:
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload_dict = payload if isinstance(payload, dict) else {}
        record = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "post_type": payload_dict.get("post_type") or payload_dict.get("postType"),
            "message_type": payload_dict.get("message_type") or payload_dict.get("messageType"),
            "self_id": payload_dict.get("self_id") or payload_dict.get("selfId"),
            "user_id": payload_dict.get("user_id") or payload_dict.get("userId"),
            "group_id": payload_dict.get("group_id") or payload_dict.get("groupId"),
            "raw_message": payload_dict.get("raw_message") or payload_dict.get("rawMessage"),
            "message": payload_dict.get("message"),
            "error": payload_dict.get("error"),
            "payload": payload,
        }
        with self.event_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def serve(
    service: BotService,
    host: str = "127.0.0.1",
    port: int = 8000,
    onebot_config: OneBotConfig | None = None,
) -> None:
    BridgeHandler.service = service
    BridgeHandler.onebot = OneBotHTTPAdapter(service, onebot_config) if onebot_config else None
    httpd = ThreadingHTTPServer((host, port), BridgeHandler)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
