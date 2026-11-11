// Cross-language contract check. Runtime inputs are bounded Pydantic snapshots.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  }
  if (typeof value === 'number' && !Number.isSafeInteger(value)) {
    throw new Error('Geometry must use safe integers; measurements use decimal strings');
  }
  return value;
}

const vectors = JSON.parse(readFileSync(new URL('../docs/contracts/hash-vectors.json', import.meta.url)));
for (const vector of vectors) {
  const hash = createHash('sha256').update(JSON.stringify(canonical(vector.payload)), 'utf8').digest('hex');
  assert.equal(hash, vector.sha256);
}
console.log(`PASS: ${vectors.length} Python/JavaScript canonical hash vectors`);
