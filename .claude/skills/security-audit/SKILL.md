---
name: security-audit
description: Use for threat modeling, privacy assessment or reviewing high-risk code changes.
---
# security-audit

Review `docs/SECURITY.md`, relevant changed code and tests. Assess tenant auth, elevation, PII/image rights, prompt injection/SSRF, file paths, secret exfiltration, external side effects, race conditions and approval replay. Findings require reproduction idea, impact and remediation. Fail closed for unresolved criticals.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
