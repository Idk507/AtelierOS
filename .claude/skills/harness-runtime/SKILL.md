---
name: harness-runtime
description: Use to implement agent lifecycle, tool broker, context engineering, memory, checkpointing or recovery.
---
# harness-runtime

Read `docs/HARNESS_CONTRACT.md`. Enforce capabilities and authorization in code, not prompt only. Bound tools by tenant, purpose, spend and time. Context builder uses relevance and allowed sources. Journal intent before external calls; stable idempotency; recovery never duplicates side effect. Separate LangGraph from tool enforcement. Test corrupt outputs, injection, retries, cancellation, approval interruption.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
