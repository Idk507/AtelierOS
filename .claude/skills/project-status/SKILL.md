---
name: project-status
description: Use to summarize actual AtelierOS development progress or recover context after compaction.
---
# project-status

Read only `docs/STATUS.md`, current phase contract and `git status --short` if available. Give current gate, completed evidence, blockers, next task, and unresolved decisions. Do not reread full product proposal or recursively scan repository. If no tests have run, say NOT VERIFIED.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
