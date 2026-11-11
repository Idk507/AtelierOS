---
name: azure-openai
description: Use when configuring or integrating Azure OpenAI reasoning, vision, image generation, or embeddings.
---
# azure-openai

Use `docs/AZURE_OPENAI.md` and `.env.example` (never read real .env contents). Detect configured deployment capabilities through opt-in health checks; mock default. Separate text+vision from image generation; require a deployed image model. Capture rate limits, 429 backoff, timeouts, content filtering, latency/cost and correlation IDs. Do not send real images until explicitly enabled.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
