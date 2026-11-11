---
name: canvas-sketching
description: Use when implementing sketch canvas, technical flats, semantic garment components or AI-controlled drawing.
---
# canvas-sketching

Read `docs/CANVAS_CONTRACT.md`. Keep geometry edit as schema-validated patch on stable component IDs. Preserve user locks and history. Separate editable vector/sketch components, artistic render, and technical-flat draft. Test changed region and unchanged component invariants; never convert a generated raster into a fictitious technical pattern.

When finished, return a concise decision record (goal, edits or findings, executed checks, results, blocker, next action). Never state a task is complete without evidence.
