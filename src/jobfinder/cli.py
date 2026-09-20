from __future__ import annotations

import argparse
import logging
import sys

from jobfinder.pipeline import run_scan
from jobfinder.storage.db import Database


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
    )
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)


def cmd_scan(args: argparse.Namespace) -> int:
    source = "mock" if args.mock else args.source
    try:
        run_scan(
            source=source,
            mock=args.mock,
            max_intents=args.max_intents,
            notify=not args.no_notify,
        )
    except RuntimeError as exc:
        print(exc)
        return 1
    return 0


def cmd_telegram_chat_id(_args: argparse.Namespace) -> int:
    from dotenv import load_dotenv
    import os

    from jobfinder.notifications.telegram import fetch_chat_ids_from_updates

    load_dotenv()
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token or token.upper().startswith("YOUR_"):
        print("Set TELEGRAM_BOT_TOKEN in .env to your real bot token from @BotFather.")
        return 1
    chats = fetch_chat_ids_from_updates(token)
    if not chats:
        print(
            "No chats found. Open Telegram, find your bot, send any message (e.g. hi), then run this again."
        )
        return 1
    print("Use one of these chat IDs in .env as TELEGRAM_CHAT_ID:\n")
    for c in chats:
        label = c.get("title") or c.get("username") or c.get("first_name") or "chat"
        print(f"  TELEGRAM_CHAT_ID={c['chat_id']}  ({c.get('type')}: {label})")
    return 0


def cmd_telegram_test(_args: argparse.Namespace) -> int:
    from jobfinder.config import load_profile
    from jobfinder.notifications.telegram import TelegramNotifier
    from jobfinder.storage.db import Database

    profile = load_profile()
    profile.notifications.telegram.enabled = True
    notifier = TelegramNotifier(profile, Database())
    if notifier.send_test_message():
        print("Test message sent.")
        return 0
    print("Telegram not configured or send failed. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    return 1


def cmd_stats(_args: argparse.Namespace) -> int:
    db = Database()
    db.init_schema()
    counts = db.job_counts()
    run = db.latest_search_run()
    print("Job counts:")
    print(f"  Total:   {counts['total']}")
    print(f"  New:     {counts['new']}")
    print(f"  Seen:    {counts['seen']}")
    print(f"  Ignored: {counts['ignored']}")
    if run:
        print("\nLatest search run:")
        for key in (
            "source",
            "queries_attempted",
            "candidates_discovered",
            "parsed",
            "rejected",
            "duplicates",
            "new_opportunities",
            "high_confidence",
        ):
            print(f"  {key}: {run.get(key)}")
    else:
        print("\nNo search runs yet. Run: python -m jobfinder scan --mock")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "jobfinder.web.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobfinder", description="Personal Job Finder")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Run discovery scan")
    scan.add_argument("--mock", action="store_true", help="Use mock discovery")
    scan.add_argument(
        "--source",
        default="linkedin",
        choices=["linkedin", "mock"],
        help="Discovery source (default: linkedin)",
    )
    scan.add_argument("--max-intents", type=int, default=None, help="Cap search intents / query budget")
    scan.add_argument("--no-notify", action="store_true", help="Skip Telegram notifications")
    scan.set_defaults(func=cmd_scan)

    tg_test = sub.add_parser("telegram-test", help="Send one test Telegram message")
    tg_test.set_defaults(func=cmd_telegram_test)

    tg_chat = sub.add_parser(
        "telegram-chat-id",
        help="List chat IDs from getUpdates (message your bot first)",
    )
    tg_chat.set_defaults(func=cmd_telegram_chat_id)

    stats = sub.add_parser("stats", help="Show database statistics")
    stats.set_defaults(func=cmd_stats)

    serve = sub.add_parser("serve", help="Start local web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
