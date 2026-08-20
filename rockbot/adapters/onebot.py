from __future__ import annotations

import base64
import json
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from rockbot.models import BotReply
from rockbot.service import BotService


@dataclass(slots=True)
class OneBotConfig:
    api_base_url: str = "http://127.0.0.1:3000"
    access_token: str = ""
    bot_name: str = "友哈巴赫"
    quick_reply: bool = False
    image_mode: Literal["base64", "file-uri", "path"] = "base64"
    enable_recent_poll: bool = False
    recent_poll_interval: float = 0.35
    api_timeout: float = 15.0
    send_retries: int = 2
    send_retry_delay: float = 0.35
    runtime_log_path: str = "logs/onebot-runtime.log"


class OneBotHTTPAdapter:
    """Minimal OneBot v11 HTTP POST adapter for NapCat/OneBot runtimes."""

    def __init__(self, service: BotService, config: OneBotConfig | None = None) -> None:
        self.service = service
        self.config = config or OneBotConfig()
        self._handled_fallback_msg_ids: set[str] = set()
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        if self.config.enable_recent_poll:
            self.start_recent_polling()

    def start_recent_polling(self) -> None:
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._poll_thread = threading.Thread(target=self._recent_poll_loop, name="rockbot-recent-poll", daemon=True)
        self._poll_thread.start()

    def stop_recent_polling(self) -> None:
        self._poll_stop.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=2)

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        event = self._normalize_event(event)
        if not event.get("post_type"):
            self._log("empty_event", onebot_event=event)
            fallback = self._handle_empty_event_fallback()
            if fallback is not None:
                return fallback
        if event.get("post_type") not in {"message", "message_sent"}:
            self._log("ignored_event", onebot_event=event, reason="unsupported_post_type")
            return {"ok": True, "handled": False}

        message = self._to_bot_message(event)
        if not message:
            self._log("ignored_event", onebot_event=event, reason="not_a_command")
            return {"ok": True, "handled": False}

        service_started = time.perf_counter()
        reply = self.service.handle_message(message)
        service_ms = self._elapsed_ms(service_started)
        if reply is None:
            self._log("ignored_event", onebot_event=event, message=message, reason="service_not_triggered")
            return {"ok": True, "handled": False}

        if self.config.quick_reply:
            self._log(
                "quick_reply",
                onebot_event=event,
                message=message,
                ok=reply.ok,
                has_text=bool(reply.text),
                has_image=bool(reply.image_path),
                service_ms=service_ms,
                total_ms=self._elapsed_ms(started),
            )
            return {"reply": self._reply_segments(reply)}

        send_result = self._send_reply(event, reply)
        total_ms = self._elapsed_ms(started)
        self._log(
            "handled_event",
            onebot_event=event,
            message=message,
            ok=reply.ok and send_result.get("ok", True),
            has_text=bool(reply.text),
            has_image=bool(reply.image_path),
            image_path=reply.image_path,
            service_ms=service_ms,
            send_ms=send_result.get("send_ms", 0),
            total_ms=total_ms,
            send_result=send_result,
        )
        return {"ok": reply.ok and send_result.get("ok", True), "handled": True, "service_ms": service_ms, "send_ms": send_result.get("send_ms", 0), "total_ms": total_ms}

    def _to_bot_message(self, event: dict[str, Any]) -> str | None:
        message_type = event.get("message_type")
        raw_message = str(event.get("raw_message") or "")
        message = event.get("message")
        self_id = str(event.get("self_id") or "")
        user_id = str(event.get("user_id") or "")
        is_self_message = bool(self_id and user_id == self_id)
        self_id_variants = {self_id, str(int(self_id)) if self_id.isdigit() else self_id}

        if message_type == "private":
            text = self._extract_text(message) or raw_message
            if text.strip().startswith("@"):
                return text
            if text.strip().startswith(("查询", "配种")):
                return text.strip()
            if is_self_message:
                return None
            return None

        if message_type != "group":
            return None

        plain_text = self._extract_text(message) or raw_message
        if plain_text.strip().startswith(("查询", "配种")):
            return plain_text.strip()
        if raw_message.strip().startswith(("查询", "配种")):
            return raw_message.strip()

        mentioned, text = self._extract_group_text(message, raw_message, self_id_variants)
        if not mentioned and raw_message.lstrip().startswith(f"@{self.config.bot_name}"):
            return raw_message
        if not mentioned:
            return None
        return f"@{self.config.bot_name} {text.strip()}".strip()

    def _extract_group_text(self, message: Any, raw_message: str, self_id_variants: set[str]) -> tuple[bool, str]:
        if isinstance(message, list):
            mentioned = False
            text_parts: list[str] = []
            for segment in message:
                if not isinstance(segment, dict):
                    continue
                segment_type = segment.get("type")
                data = segment.get("data") or {}
                if segment_type == "at" and str(data.get("qq")) in self_id_variants | {"all"}:
                    mentioned = True
                elif segment_type == "text":
                    text_parts.append(str(data.get("text", "")))
            return mentioned, "".join(text_parts)

        for one_id in self_id_variants:
            if not one_id:
                continue
            cq_at = rf"\[CQ:at,qq={re.escape(one_id)}\]"
            if re.search(cq_at, raw_message):
                return True, re.sub(cq_at, "", raw_message).strip()
        if raw_message.lstrip().startswith(f"@{self.config.bot_name}"):
            return True, raw_message.lstrip()[len(self.config.bot_name) + 1 :].strip()
        return False, raw_message

    def _extract_text(self, message: Any) -> str:
        if isinstance(message, list):
            return "".join(
                str((segment.get("data") or {}).get("text", ""))
                for segment in message
                if isinstance(segment, dict) and segment.get("type") == "text"
            )
        return str(message or "")

    def _send_reply(self, event: dict[str, Any], reply: BotReply) -> dict[str, Any]:
        started = time.perf_counter()
        message_type = event.get("message_type")
        if message_type == "group":
            action = "send_group_msg"
            base_payload = {"group_id": event.get("group_id")}
        elif message_type == "private":
            action = "send_private_msg"
            base_payload = {"user_id": event.get("user_id")}
        else:
            return {"ok": False, "error": "unsupported_message_type", "send_ms": self._elapsed_ms(started)}

        sent: list[str] = []
        if reply.text:
            text_segments = [{"type": "text", "data": {"text": reply.text}}]
            self._call_api_with_retry(action, {**base_payload, "message": text_segments})
            sent.append("text")
        if not reply.image_path:
            return {"ok": True, "sent": sent, "send_ms": self._elapsed_ms(started)}

        image_path = Path(reply.image_path)
        mode_errors: list[dict[str, str]] = []
        for mode in self._image_mode_attempts():
            try:
                self._call_api_with_retry(
                    action,
                    {
                        **base_payload,
                        "message": [
                            {
                                "type": "image",
                                "data": {"file": self._image_file_value(image_path, mode)},
                            }
                        ],
                    },
                )
                sent.append(f"image:{mode}")
                return {"ok": True, "sent": sent, "image_mode": mode, "send_ms": self._elapsed_ms(started)}
            except RuntimeError as exc:
                mode_errors.append({"mode": mode, "error": str(exc)})
                continue

        if reply.ok:
            self._call_api_with_retry(
                action,
                {
                    **base_payload,
                    "message": [
                        {
                            "type": "text",
                            "data": {"text": f"\n图片发送失败，本地图片已生成：{image_path.resolve()}"},
                        }
                    ],
                },
            )
            sent.append("image_failure_text")
        return {"ok": False, "sent": sent, "errors": mode_errors, "send_ms": self._elapsed_ms(started)}

    def _reply_segments(self, reply: BotReply) -> list[dict[str, dict[str, str]]]:
        segments: list[dict[str, dict[str, str]]] = []
        if reply.text:
            segments.append({"type": "text", "data": {"text": reply.text}})
        if reply.image_path:
            segments.append(
                {
                    "type": "image",
                    "data": {"file": self._image_file_value(Path(reply.image_path), self.config.image_mode)},
                }
            )
        return segments

    def _image_mode_attempts(self) -> list[Literal["base64", "file-uri", "path"]]:
        modes: list[Literal["base64", "file-uri", "path"]] = [self.config.image_mode]
        for mode in ("file-uri", "path", "base64"):
            if mode not in modes:
                modes.append(mode)
        return modes

    def _image_file_value(self, image_path: Path, mode: Literal["base64", "file-uri", "path"]) -> str:
        path = image_path.resolve()
        if mode == "path":
            return str(path)
        if mode == "file-uri":
            return path.as_uri()
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"base64://{encoded}"

    def _call_api(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.api_base_url.rstrip('/')}/{action}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                **self._auth_headers(),
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.config.api_timeout) as response:
                text = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            self._log("api_error", action=action, error=str(exc), elapsed_ms=self._elapsed_ms(started))
            raise RuntimeError(f"OneBot API 调用失败：{exc}") from exc
        result = json.loads(text or "{}")
        if result.get("status") == "failed" or int(result.get("retcode", 0) or 0) != 0:
            self._log("api_error", action=action, result=result, elapsed_ms=self._elapsed_ms(started))
            raise RuntimeError(f"OneBot API 调用失败：{result}")
        self._log("api_ok", action=action, elapsed_ms=self._elapsed_ms(started))
        return result

    def _call_api_with_retry(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: RuntimeError | None = None
        attempts = max(1, self.config.send_retries + 1)
        for attempt in range(1, attempts + 1):
            try:
                result = self._call_api(action, payload)
                if attempt > 1:
                    self._log("api_retry_recovered", action=action, attempt=attempt)
                return result
            except RuntimeError as exc:
                last_error = exc
                self._log("api_retry", action=action, attempt=attempt, attempts=attempts, error=str(exc))
                if attempt < attempts:
                    time.sleep(self.config.send_retry_delay * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("OneBot API 调用失败")

    def _auth_headers(self) -> dict[str, str]:
        if not self.config.access_token:
            return {}
        return {"Authorization": f"Bearer {self.config.access_token}"}

    def _handle_empty_event_fallback(self) -> dict[str, Any] | None:
        deadline = time.monotonic() + 1.8
        while True:
            result = self._handle_recent_contact_once(send_reply=True)
            if result and result.get("handled"):
                return result
            if time.monotonic() >= deadline:
                return result
            time.sleep(0.12)

    def _recent_poll_loop(self) -> None:
        self._seed_recent_contact_ids()
        while not self._poll_stop.wait(self.config.recent_poll_interval):
            self._handle_recent_contact_once(send_reply=True)

    def _seed_recent_contact_ids(self) -> None:
        try:
            result = self._call_api("get_recent_contact", {"count": 10})
        except RuntimeError:
            self._log("recent_seed_failed")
            return
        for contact in result.get("data", []):
            if isinstance(contact, dict) and contact.get("msgId"):
                self._handled_fallback_msg_ids.add(str(contact["msgId"]))

    def _handle_recent_contact_once(self, send_reply: bool) -> dict[str, Any] | None:
        try:
            result = self._call_api("get_recent_contact", {"count": 10})
        except RuntimeError:
            self._log("recent_poll_failed")
            return None

        candidates: list[tuple[int, str, dict[str, Any]]] = []
        for contact in result.get("data", []):
            if not isinstance(contact, dict):
                continue
            msg_id = str(contact.get("msgId") or "")
            if not msg_id or msg_id in self._handled_fallback_msg_ids:
                continue
            latest_msg = contact.get("lastestMsg")
            if not isinstance(latest_msg, dict):
                continue
            event = self._normalize_event(latest_msg)
            if event.get("post_type") not in {"message", "message_sent"}:
                continue
            if not self._to_bot_message(event):
                continue
            try:
                msg_time = int(contact.get("msgTime") or latest_msg.get("time") or 0)
            except (TypeError, ValueError):
                msg_time = 0
            candidates.append((msg_time, msg_id, event))

        for _msg_time, msg_id, event in sorted(candidates, reverse=True):
            self._handled_fallback_msg_ids.add(msg_id)
            if len(self._handled_fallback_msg_ids) > 200:
                self._handled_fallback_msg_ids = set(list(self._handled_fallback_msg_ids)[-100:])
            if not send_reply:
                self._log("recent_seeded_message", msg_id=msg_id)
                return {"ok": True, "handled": True, "fallback": "seeded"}
            self._log("recent_poll_command", msg_id=msg_id)
            return self.handle_event(event)

        return {"ok": True, "handled": False, "fallback": "no recent command"}

    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        aliases = {
            "post_type": "postType",
            "message_type": "messageType",
            "sub_type": "subType",
            "self_id": "selfId",
            "user_id": "userId",
            "group_id": "groupId",
            "raw_message": "rawMessage",
            "message_id": "messageId",
        }
        normalized = dict(event)
        for snake_key, camel_key in aliases.items():
            if snake_key not in normalized and camel_key in event:
                normalized[snake_key] = event[camel_key]
        return normalized

    def _log(self, event_name: str, **fields: Any) -> None:
        path = Path(self.config.runtime_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "event": event_name,
            **self._json_safe(fields),
        }
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _elapsed_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
