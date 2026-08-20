from __future__ import annotations

import argparse
import sys

from .adapters.onebot import OneBotConfig
from .cache import JsonCache
from .bridge import serve
from .config import load_web_sources
from .render import CardRenderer
from .service import BotService
from .sources import CompositeSource, ConfigurableWebSource, LocalJsonSource, SampleSource


def build_service(args: argparse.Namespace) -> BotService:
    sources = []
    if args.config:
        sources.extend(ConfigurableWebSource(config) for config in load_web_sources(args.config))
    if args.local_db:
        sources.append(LocalJsonSource(args.local_db))
    if args.sample:
        sources.append(SampleSource())
    source = CompositeSource(sources or [SampleSource()])
    return BotService(
        bot_name=args.bot_name,
        cache=JsonCache(args.cache_dir),
        source=source,
        renderer=CardRenderer(args.output_dir),
    )


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Rock Kingdom QQ bot offline core")
    parser.add_argument("message", nargs="?", help="message text, for example: @友哈巴赫 奇丽草 查蛋")
    parser.add_argument("--bot-name", default="友哈巴赫")
    parser.add_argument("--cache-dir", default="data/cache")
    parser.add_argument("--output-dir", default="outputs/cards")
    parser.add_argument("--config", help="JSON config for web data sources")
    parser.add_argument("--local-db", default="data/pets.seed.json", help="local pet database JSON")
    parser.add_argument("--no-sample", dest="sample", action="store_false", help="disable built-in sample source")
    parser.add_argument("--serve", action="store_true", help="start a local HTTP bridge instead of handling one message")
    parser.add_argument("--onebot", action="store_true", help="enable OneBot v11 HTTP POST endpoint at /onebot")
    parser.add_argument("--onebot-api-url", default="http://127.0.0.1:3000", help="NapCat/OneBot HTTP API base URL")
    parser.add_argument("--onebot-token", default="", help="OneBot HTTP access token, if configured")
    parser.add_argument("--onebot-quick-reply", action="store_true", help="reply in POST response instead of calling OneBot HTTP API")
    parser.add_argument(
        "--onebot-image-mode",
        choices=["base64", "file-uri", "path"],
        default="base64",
        help="image segment file value for OneBot replies",
    )
    parser.add_argument("--disable-recent-poll", action="store_true", help="disable NapCat recent-contact fallback polling")
    parser.add_argument("--recent-poll-interval", type=float, default=0.35, help="seconds between recent-contact fallback polls")
    parser.add_argument("--onebot-api-timeout", type=float, default=15.0, help="seconds before a OneBot API call times out")
    parser.add_argument("--onebot-send-retries", type=int, default=2, help="retry count for OneBot send API calls")
    parser.add_argument("--onebot-send-retry-delay", type=float, default=0.35, help="base seconds between send retries")
    parser.add_argument("--onebot-runtime-log", default="logs/onebot-runtime.log", help="JSONL runtime diagnostics log path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.set_defaults(sample=True)
    args = parser.parse_args(argv)

    if args.serve:
        service = build_service(args)
        onebot_config = None
        if args.onebot:
            onebot_config = OneBotConfig(
                api_base_url=args.onebot_api_url,
                access_token=args.onebot_token,
                bot_name=args.bot_name,
                quick_reply=args.onebot_quick_reply,
                image_mode=args.onebot_image_mode,
                enable_recent_poll=not args.disable_recent_poll,
                recent_poll_interval=args.recent_poll_interval,
                api_timeout=args.onebot_api_timeout,
                send_retries=args.onebot_send_retries,
                send_retry_delay=args.onebot_send_retry_delay,
                runtime_log_path=args.onebot_runtime_log,
            )
        print(f"HTTP bridge listening on http://{args.host}:{args.port}")
        if args.onebot:
            print(f"OneBot endpoint: http://{args.host}:{args.port}/onebot")
            print(f"OneBot API target: {args.onebot_api_url}")
            print(f"OneBot image mode: {args.onebot_image_mode}")
            print(f"OneBot runtime log: {args.onebot_runtime_log}")
        serve(service, host=args.host, port=args.port, onebot_config=onebot_config)
        return 0

    if not args.message:
        parser.print_help()
        return 2

    service = build_service(args)
    reply = service.handle_message(args.message)
    if reply is None:
        print("未触发机器人。请以 @友哈巴赫 开头。")
        return 1

    print(reply.text)
    if reply.image_path:
        print(reply.image_path)
    return 0 if reply.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
