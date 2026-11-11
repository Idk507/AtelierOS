"""Validate packaged project configuration without network calls or dependencies."""
from __future__ import annotations
import json
import pathlib
import re
import sys


def main() -> int:
    """Ensure all expected files, frontmatter and Claude settings are structurally sound."""
    project = pathlib.Path(__file__).resolve().parents[2]
    failures: list[str] = []
    required = ["CLAUDE.md", "README.md", "docs/STATUS.md", "docs/BUILD_PLAN.md", ".env.example"]
    for name in required:
        if not (project / name).is_file():
            failures.append(f"Missing {name}")
    try:
        settings = json.loads((project / ".claude/settings.json").read_text(encoding="utf-8"))
        if not isinstance(settings.get("hooks"), dict):
            failures.append("No hooks in settings")
        if not isinstance(settings.get("permissions"), dict):
            failures.append("No permissions in settings")
    except (OSError, ValueError) as exc:
        failures.append(f"Invalid settings: {exc}")
    for folder in ("agents", "skills"):
        paths = list((project / ".claude" / folder).rglob("*.md"))
        if not paths:
            failures.append(f"Empty {folder}")
        for file in paths:
            body = file.read_text(encoding="utf-8")
            if not body.startswith("---\n") or "\n---\n" not in body[4:]:
                failures.append(f"Malformed YAML frontmatter: {file.relative_to(project)}")
            if not re.search(r"(?m)^name: [a-z0-9-]+$", body):
                failures.append(f"Missing valid name: {file.relative_to(project)}")
    for path in (project / ".claude").rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            failures.append(f"Invalid {path.relative_to(project)}: {exc}")
    if failures:
        print("FAILED: " + "; ".join(failures))
        return 1
    print("PASS: scaffold paths, JSON settings and skill/agent frontmatter present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
