from __future__ import annotations

import argparse
import logging
import sys

from jobfinder.pipeline import run_mock_scan
from jobfinder.storage.db import Database


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


def cmd_scan(args: argparse.Namespace) -> int:
    if not args.mock:
        print("Phase 1 supports only mock discovery. Use: python -m jobfinder scan --mock")
        return 1
    run_mock_scan(max_intents=args.max_intents)
    return 0


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
    scan.add_argument("--mock", action="store_true", help="Use mock discovery (Phase 1)")
    scan.add_argument("--max-intents", type=int, default=None, help="Cap search intents")
    scan.set_defaults(func=cmd_scan)

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
