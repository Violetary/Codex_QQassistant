from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .service import BotService


class BridgeHandler(BaseHTTPRequestHandler):
    service: BotService

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

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def serve(service: BotService, host: str = "127.0.0.1", port: int = 8000) -> None:
    BridgeHandler.service = service
    httpd = ThreadingHTTPServer((host, port), BridgeHandler)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
