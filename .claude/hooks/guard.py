"""Best-effort Claude Code PreToolUse safeguard for obvious unsafe operations.

This guard is deliberately conservative and not a sandbox. It does not replace
Claude Code permissions, a restricted execution environment or backend IAM.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import PurePosixPath
from typing import Any


SECRET_FILES = re.compile(r"(?:^|[/\\])\.env(?:\.[^/\\]+)?$|(?:^|[/\\])(?:id_rsa|id_ed25519)$", re.I)
DANGEROUS_COMMANDS = [
    re.compile(r"\b(?:rm\s+-rf|git\s+clean\s+-fd|git\s+reset\s+--hard)\b", re.I),
    re.compile(r"\b(?:drop\s+database|drop\s+schema|truncate\s+table)\b", re.I),
    re.compile(r"\b(?:terraform\s+destroy|kubectl\s+delete\s+namespace)\b", re.I),
    re.compile(r"\b(?:curl|wget)\b.*\|\s*(?:sh|bash|powershell)\b", re.I),
]


def evaluate(payload: dict[str, Any]) -> str | None:
    """Return a reason to block a known-dangerous tool request, otherwise None."""
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or {}
    if not isinstance(data, dict):
        return "Malformed tool input"
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(data.get("file_path") or data.get("notebook_path") or "")
        if SECRET_FILES.search(path.replace("\\", "/")):
            return "Never edit secrets or private keys through Claude Code"
    if tool == "Bash":
        command = str(data.get("command") or "")
        if any(rule.search(command) for rule in DANGEROUS_COMMANDS):
            return "Destructive or piped remote shell command requires a human-run procedure"
    return None


def main() -> int:
    """Read hook JSON from stdin and block on obvious prohibited operations."""
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("JSON root must be an object")
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Unable to validate tool request: {exc}", file=sys.stderr)
        return 2
    reason = evaluate(payload)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
