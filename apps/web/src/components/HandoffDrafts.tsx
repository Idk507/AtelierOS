'use client';import { useEffect, useState } from 'react';import { api } from '@/lib/api';import type { Garment } from '@/lib/types';
interface Draft {id: string; revision_id: string; current: boolean}
interface Review {status: string; current: boolean; digest: string; package: {revision_id: string; revision_digest: string; measurements?: unknown; material_offer?: unknown; material_estimate?: unknown; sample_feedback?: unknown}}

function ReviewSummary({route}: {route: string}) {
  const [review, setReview] = useState<Review | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  async function load() {
    setLoading(true); setError('');
    try {setReview(await api<Review>(route));}
    catch {setError('Could not load review contents. Try again.');}
    finally {setLoading(false);}
  }
  return <details onToggle={event => {if (event.currentTarget.open && !review && !loading) void load();}}>
    <summary>Review contents and open questions</summary>
    {loading && <p role="status">Loading review contents…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {review && <>
      <p><strong>{review.status.replaceAll('_', ' ')}</strong> · {review.current ? 'Current revision' : 'Historical revision'}</p>
      {([['Measurements and provenance', review.package.measurements], ['Material evidence', review.package.material_offer], ['Cost estimate', review.package.material_estimate], ['Sample findings and resolutions', review.package.sample_feedback]] as [string, unknown][]).map(([label, value]) => <details key={label}>
        <summary>{label}</summary>
        <pre style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>{value == null || (Array.isArray(value) && !value.length) ? 'No evidence recorded in this snapshot.' : JSON.stringify(value, null, 2)}</pre>
      </details>)}
      <h3>Open questions</h3>
      <ul>
        {(!review.current || review.status === 'needs_review') && <li>This package requires review against the latest revision and evidence.</li>}
        <li>Front and back views are not identified in the design model.</li>
        <li>A professional must determine required measurements, tolerances and technical completeness.</li>
        <li>Unresolved blocking sample findings require a recorded resolution.</li>
      </ul>
      <details><summary>Revision and package identifiers</summary><p style={{overflowWrap: 'anywhere'}}>Revision: {review.package.revision_id}<br/>Revision digest: {review.package.revision_digest}<br/>Package digest: {review.digest}</p></details>
    </>}
    <button type="button" className="button secondary" disabled={loading} onClick={() => void load()}>Refresh summary</button>
  </details>;
}

export function HandoffDrafts({garment, disabled}: {garment: Garment; disabled: boolean}) {
  const route = `/garments/${garment.id}/handoff`;
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const approved = garment.approved_revision_id === garment.draft_revision_id;
  useEffect(() => {
    let active = true;
    void api<Draft[]>(route).then(rows => {if (active) setDrafts(rows);})
      .catch(() => {if (active) setError('Could not load handoff drafts.');});
    return () => {active = false;};
  }, [route]);

  async function create() {
    setBusy(true); setError('');
    try {
      await api(route, {base_revision: garment.draft_revision_id});
      setDrafts(await api<Draft[]>(route));
    } catch {setError('Could not create a review draft for this revision.');}
    finally {setBusy(false);}
  }

  return <section className="inspector-section">
    <p className="eyebrow">TECHNICAL REVIEW</p><h2>Handoff drafts</h2>
    <p className="muted">{approved ? 'Export the editable design and its material evidence for patternmaker review.' : 'Approve the current aesthetic revision to prepare a handoff draft.'}</p>
    {error && <p className="error" role="alert">{error}</p>}
    <button className="button secondary" disabled={!approved || disabled || busy} onClick={() => void create()}>Prepare review draft</button>
    {drafts.map(draft => <div className="reference-card" key={draft.id}>
      <p>Revision {draft.revision_id.slice(0,8)} · {draft.current ? 'Current draft' : 'Earlier draft, review required'}</p>
      <ReviewSummary route={`${route}/${draft.id}`}/>
      <a href={`/api/backend/v1${route}/${draft.id}`} download={`atelier-${draft.revision_id.slice(0,8)}-review-draft.json`}>Download review JSON</a>
      {' · '}<a href={`/api/backend/v1${route}/${draft.id}/pdf`} download={`atelier-${draft.revision_id.slice(0,8)}-review-draft.pdf`}>Download review PDF</a>
      {' · '}<a href={`/api/backend/v1${route}/${draft.id}/html`} download="atelier-handoff.html">Download editable HTML</a>
    </div>)}
  </section>;
}
