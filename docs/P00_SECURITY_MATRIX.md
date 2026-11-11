# P00 authorization, trust and privacy supplement
Proposed controls; not implemented. In addition to SECURITY.md.

| Sensitive action | Authorized actor | Required check | Negative scenario |
|---|---|---|---|
| read project/assets/jobs/audit | active granted member | organization and project access on every resource and signed URL issue | tenant B guesses tenant A ID |
| propose edit / accept draft edit | designer or patternmaker / designer respectively | base revision, component scope, locks, typed operations | parent deletion bypasses neckline lock |
| request/authorize unlock | designer / org-admin respectively | separate human grant, exact constraint and revision | edit embeds unlock or grant replay uses new head |
| aesthetic approval | designer or client-reviewer | human session, purpose, current revision hash | agent submits approval or stale client tab |
| technical approval | patternmaker | same immutable revision and professional purpose | client claims construction approval |
| handoff approval/export | production | current revision and all required purposes, no unsupported critical facts | stale spec masquerades as current |
| catalog comparison | designer/production | evidence, units, freshness; no write to supplier | unknown stretch ranked hard-compatible |
| upload/feedback | designer/patternmaker | asset ownership, consent, source revision | cross-tenant photo or fabricated measurement |
| research/visual jobs | designer | rights, scoped retrieval, enabled capability, budgets | malicious source requests secret/tool access |
| supplier contact/purchase | none in P00â€“P08 | disabled; future explicit authenticated approval | replay sends duplicate RFQ |

Org-admin manages membership and unlock decisions, but does not inherit aesthetic, technical or purchasing approval authority. Multiple roles must be explicitly assigned. Workers recheck resource scope and capability before execution; revocation invalidates pending authorization.

Uploads: private quarantine, MIME signature/extension validation, configured size/pixel/page limits, decompression limits, metadata removal and malware scanning before processing. Isolate PDF/image renderers; deny active HTML and paths supplied by users. Reject oversized or corrupted assets without logging contents. Numeric limits are an implementation entry contract, not a claim of existing enforcement.

Retrieval: authorize before query and each result; reject loopback/private/link-local/metadata IPs including redirects and DNS re-resolution; safe egress proxy, bounded content and timeouts. Retrieved text cannot select tools or change policy. Unknown image rights prohibit reuse in moodboards, prompts and exports; link-only citations may remain if allowed.

Approval races: transaction rechecks role, membership, revision head, hash and lock state; failed transaction emits no successful approval/outbox. Idempotency response lookup reauthorizes caller. Audit denied attempts with redacted identifiers and reason category; no secrets, raw prompts, images or measurement tables in logs.

Proposed retention defaults for review: synthetic fixtures retained with repository; live photos disabled until consent/deletion workflow accepted. Future raw uploads 30 days, deleted-user assets purge within 30 days except documented legal holds; audit metadata 365 days without raw media; backups expire within 35 days. These defaults require data-owner and jurisdiction review, not a compliance claim. Track deletion across derived assets and embeddings; signed URLs expire within 5 minutes. No live ingestion before that gate.
