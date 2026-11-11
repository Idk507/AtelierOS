---
name: eval-run
description: Use when adding or running agent/model benchmarks, regression experiments or Harness² optimization.
---
# eval-run

Read `docs/EVALS.md`. Select fixed fixture subset and budget; deterministic metrics first. Log model provider, deployment, prompt/skill hashes, latency, token cost, constraint violations and approvals. Never compare mock to live as equivalent. Agent modifications cannot bypass frozen tests or approval.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
