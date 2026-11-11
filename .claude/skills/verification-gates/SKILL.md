---
name: verification-gates
description: Use before completing a phase, reporting a demo, making a release decision, or claiming an integration works.
---
# verification-gates

Read `docs/EVALS.md`, selected `docs/phases/Pxx.md`, and `docs/SECURITY.md`. Require executed tests with commands, output summary, fixture provenance and coverage of failures. Clearly distinguish mock/live/provider/access unavailable. Rejected or incomplete gates remain unresolved; do not forge evidence.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
