# Editable canvas contract

> P00 reconciliation: P00_CONTRACTS.md governs proposed route, field, event and lifecycle semantics; P00_SCOPE.md supplies stable journey names. Older examples below are historical where inconsistent.


Semantic nodes: garment, bodice, neckline, sleeve, collar, hem, closure, embroidery placement, textile zone and freehand notes. Every node carries stable id, parent, layer, transform, geometry (vector or freehand path), lock status, provenance and last-edit revision. Canvas patches target IDs, not pixels; support create/update/delete/group/move/transform with optimistic concurrency. tldraw is a presentation/editor adapter; canonical changes are validated by backend patch service before commit. A rendered concept links to the exact source revision, image prompt and source assets but never overwrites source vectors. Technical-flat mode uses separate conventions, dimensions and manual verification. Test per-component edit fidelity, lock violations, undo, replay and restore after reload.
