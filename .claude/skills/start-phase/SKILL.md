---
name: start-phase
description: Use when the user requests to start or continue a numbered AtelierOS build phase.
---
# start-phase

Read `docs/STATUS.md` and the selected `docs/phases/Pxx.md`. Check dependencies and previous gate first. Provide a bounded implementation plan for exactly one phase or one vertical slice within it. Identify security and tests. Delegate a narrowly scoped task to the relevant development agent if useful; do not commission all agents. If phase is P00 produce design artifacts, not implementation. Update status with real results. Stop on phase gate for architect review.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
