from __future__ import annotations

import argparse
import sys

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
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--config", help="JSON config for web data sources")
    parser.add_argument("--local-db", default="data/pets.seed.json", help="local pet database JSON")
    parser.add_argument("--no-sample", dest="sample", action="store_false", help="disable built-in sample source")
    parser.add_argument("--serve", action="store_true", help="start a local HTTP bridge instead of handling one message")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.set_defaults(sample=True)
    args = parser.parse_args(argv)

    if args.serve:
        service = build_service(args)
        print(f"HTTP bridge listening on http://{args.host}:{args.port}")
        serve(service, host=args.host, port=args.port)
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
