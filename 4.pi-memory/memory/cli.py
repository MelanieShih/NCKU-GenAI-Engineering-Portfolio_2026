"""CLI for memory capture/retrieve/inject/recall/forget."""
from __future__ import annotations

import argparse
import json
import sys

from .core import (
    build_injection,
    capture,
    forget,
    list_memories,
    make_observation,
    retrieve,
)


def _parse_mode(value: str | None) -> str | None:
    if value is None:
        return None
    mode = value.strip().lower()
    if mode not in {"bm25", "hybrid"}:
        raise argparse.ArgumentTypeError("mode must be one of: bm25, hybrid")
    return mode


def _parse_decay(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"on", "true", "1", "yes"}:
        return True
    if lowered in {"off", "false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError("decay must be one of: on, off")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m memory.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--summary", required=True)
    capture_parser.add_argument("--session", default="cli")
    capture_parser.add_argument("--tags", default="")

    retrieve_parser = sub.add_parser("retrieve")
    retrieve_parser.add_argument("--query", required=True)
    retrieve_parser.add_argument("--k", type=int, default=8)
    retrieve_parser.add_argument("--mode", type=_parse_mode, default=None)
    retrieve_parser.add_argument("--decay", type=_parse_decay, default=None)

    inject_parser = sub.add_parser("inject")
    inject_parser.add_argument("--query", required=True)
    inject_parser.add_argument("--budget", type=int, default=2000)
    inject_parser.add_argument("--k", type=int, default=8)
    inject_parser.add_argument("--mode", type=_parse_mode, default=None)
    inject_parser.add_argument("--decay", type=_parse_decay, default=None)

    recall_parser = sub.add_parser("recall")
    recall_parser.add_argument("--query", default=None)
    recall_parser.add_argument("--k", type=int, default=8)
    recall_parser.add_argument("--mode", type=_parse_mode, default=None)
    recall_parser.add_argument("--decay", type=_parse_decay, default=None)
    recall_parser.add_argument("--list", type=int, default=0, help="List first N memories without ranking")

    forget_parser = sub.add_parser("forget")
    forget_parser.add_argument("--id", required=True, help="Memory id to remove")

    args = parser.parse_args(argv)

    if args.cmd == "capture":
        tags = [tag for tag in args.tags.split(",") if tag]
        capture(make_observation(args.summary, session_id=args.session, tags=tags))
        print(f"Remembered: {args.summary}")
        return

    if args.cmd == "retrieve":
        rows = retrieve(args.query, args.k, mode=args.mode, apply_decay=args.decay)
        print(json.dumps(rows, ensure_ascii=False))
        return

    if args.cmd == "inject":
        out = build_injection(args.query, args.budget, k=args.k, mode=args.mode, apply_decay=args.decay)
        sys.stdout.write(out)
        return

    if args.cmd == "recall":
        if args.list and args.list > 0:
            rows = list_memories(args.list)
        else:
            query = args.query or ""
            rows = retrieve(query, args.k, mode=args.mode, apply_decay=args.decay)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if args.cmd == "forget":
        ok = forget(args.id)
        print(f"Forgot: {args.id}" if ok else f"Not found: {args.id}")
        return


if __name__ == "__main__":
    main()
