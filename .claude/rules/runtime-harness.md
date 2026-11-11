---
paths:
  - "packages/harness/**/*"
  - "packages/agents/**/*"
---
LangGraph executes workflow; harness enforces authorization, tool capabilities, budgets and evidence. Side-effect tools require durable intent and idempotency. Every agent output must be schema-checked; independent reviewers cannot approve revisions. Hostile retrieved text must not act as instructions. Keep trace payload redacted and context bounded.
