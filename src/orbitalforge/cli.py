from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .engine import tick
from .state import read_state
from .validate import validate_repository


def main() -> None:
    parser = argparse.ArgumentParser(prog="orbitalforge")
    parser.add_argument("command", choices=["tick", "status", "validate", "preflight"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--all-projects", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    try:
        if args.command == "tick":
            print(tick(root))
        elif args.command == "status":
            print(json.dumps(read_state(root).to_dict(), indent=2))
        elif args.command == "validate":
            print("\n".join(validate_repository(root, args.all_projects)))
        elif args.command == "preflight":
            if not os.getenv("GROQ_API_KEY"):
                raise RuntimeError("GROQ_API_KEY is not configured")
            validate_repository(root, False)
            print("preflight ok")
    except Exception as exc:
        print(f"OrbitalForge {args.command} failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
