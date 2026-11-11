"""Lightweight post-edit guard: syntax-validate changed JSON without modifying it."""
from __future__ import annotations
import json
import sys
from pathlib import Path


def main() -> int:
    """Inspect hook input and validate relevant JSON files if they are available."""
    try:
        data = json.load(sys.stdin)
    except (ValueError, json.JSONDecodeError):
        return 0
    inp = data.get("tool_input") or {}
    raw = inp.get("file_path") if isinstance(inp, dict) else None
    if not isinstance(raw, str) or not raw.endswith(".json"):
        return 0
    path = Path(raw)
    if not path.is_file() or path.stat().st_size > 1_000_000:
        return 0
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"JSON validation failed in {path}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
