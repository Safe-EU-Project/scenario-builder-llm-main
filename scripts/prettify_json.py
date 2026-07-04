#!/usr/bin/env python3
"""
Pretty-print JSON (UTF-8, indented) without altering string values or key names.

Examples:
  curl -s ... > raw.json
  python scripts/prettify_json.py raw.json > pretty.json

  # Only the scenario subtree (same data, less noise than full response):
  python scripts/prettify_json.py raw.json --key scenario > scenario_pretty.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _navigate(data: Any, path: str) -> Any:
    cur = data
    for part in path.split("."):
        part = part.strip()
        if not part:
            continue
        if isinstance(cur, dict):
            if part not in cur:
                raise KeyError(part)
            cur = cur[part]
        else:
            raise TypeError(f"Cannot descend into {type(cur).__name__} at {part!r}")
    return cur


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "path",
        nargs="?",
        help="Input JSON file (omit or use '-' for stdin)",
    )
    p.add_argument(
        "--key",
        metavar="PATH",
        help="Dot-separated path into JSON (e.g. scenario). Prints only that subtree.",
    )
    args = p.parse_args()

    if not args.path or args.path == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.path, encoding="utf-8") as f:
            data = json.load(f)

    if args.key:
        data = _navigate(data, args.key)

    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
