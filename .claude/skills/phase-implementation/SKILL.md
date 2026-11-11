---
name: phase-implementation
description: Use when implementing a single reviewed phase or bounded feature slice in AtelierOS.
---
# phase-implementation

Read current `docs/phases/Pxx.md` and only relevant interface contracts. Make a compact file-change plan. Implement tests-first for correctness critical paths, with typed docstrings and error handling. Do not create fake integrations. Run unit checks and relevant linters; persist factual results in `docs/STATUS.md`; stop at explicit gate.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
