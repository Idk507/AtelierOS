# Threat model and security acceptance

## Assets and trust boundaries
Sensitive fashion designs, client images/measurements, catalog contracts, supplier correspondence, keys, organization memberships, and approval decisions. Threat boundaries: internet search results (untrusted), external reference images, PDFs, model output, browser canvas actions, tenant requests, background workers and supplier channels.

## Controls
Tenant ID comes from authenticated claims, never trusted client body alone. Role-based actions include designer, client-reviewer, patternmaker, production, org-admin; enforce resource-scoped checks on every endpoint and worker action. TLS for transfers, encrypted storage, encrypted database backups and shortest practical object-signed-URL TTL. Use managed identity where practical, otherwise securely stored API keys with rotation; never place secrets in .claude, Git or trace text. Retention/deletion for user photos and image inputs; consent for likeness use. Maintain append-only audit actions for approvals and tool side effects.

## Agents and tools
Tool broker validates schema, allowed tool set, data tenancy, maximum spending, output size, DNS/IP restrictions and path constraints. Search-result text must not be allowed to override system rules or invoke tools. SSRF protection includes private/loopback/cloud metadata address filtering and redirect validation. External data cannot approve revisions. HTML/PDF rendering is isolated and unprivileged. Only explicit, authenticated human action may trigger supplier contact, purchasing or production approval. Prompt instructions and hooks are not sufficient enforcement.

## Development environment
The bundled PreToolUse hook is a best-effort guard to catch obvious accidental destructive commands and edits to `.env`; it is NOT a sandbox or complete policy layer. Use Claude Code permissions and OS/container isolation for trusted execution. Run migrations on disposable DB until approved; never auto-apply production migrations.

## Gate tests
Cross-tenant read/write, IDOR, stale revision approval, forged approval hash, tampered catalog offers, prompt-injection tool escalation, malicious URL/redirect, image metadata privacy, duplicate provider callback, replayed requests, forbidden secrets output, oversized assets, corrupted job checkpoint, cancellation and cost cap. Record evidence and remaining risk for each gate.

## P00 supplement
See P00_SECURITY_MATRIX.md for proposed action-by-role rules, upload and retrieval handling, race protection, redaction and retention defaults. Controls remain unimplemented.
