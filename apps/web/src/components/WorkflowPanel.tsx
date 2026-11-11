'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Garment, Patch } from '@/lib/types';

interface Run {
  id: string;
  revision_id: string;
  mode: 'concept' | 'geometry';
  status: 'awaiting_review' | 'approved' | 'rejected' | 'cancelled';
  checkpoint_digest: string;
  created_by_viewer: boolean;
  proposal_id: string | null;
  result: { thumbnail_jpeg?: string; operations?: Patch[] };
}

export function WorkflowPanel({garment, changes, onOpenProposal}: {
  garment: Garment;
  changes: Patch[];
  onOpenProposal: (id: string, operations: Patch[]) => Promise<void>;
}) {
  const route = `/garments/${garment.id}/workflows`;
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const patch = changes[0];
  const editable = changes.length === 1 && patch?.op === 'update' &&
    Object.keys(patch.payload).length === 1 && Array.isArray(patch.payload.geometry) &&
    patch.payload.geometry.length >= 4 && patch.payload.geometry.length <= 256;

  useEffect(() => {
    let active = true;
    void api<Run[]>(route).then(data => {if (active) setRuns(data);})
      .catch(() => {if (active) setError('Could not load workflow reviews.');});
    return () => {active = false;};
  }, [route]);

  async function perform(path: string, body: Record<string, unknown>) {
    setError('');
    setBusy(true);
    try {
      await api(path, {base_revision: garment.draft_revision_id, ...body});
      setRuns(await api<Run[]>(route));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Workflow could not be saved.');
    } finally {setBusy(false);}
  }

  return <section className="inspector-section research-board" aria-label="Workflow reviews">
    <p className="eyebrow">INDEPENDENT REVIEW</p>
    <h2>Workflow reviews</h2>
    <p className="muted">Generate a sample concept or send one canvas geometry edit to another studio member for review.</p>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="compact-form">
      <button className="button secondary" disabled={busy}
        onClick={() => void perform(route, {mode: 'concept'})}>Create fixture concept</button>
      <button className="button secondary" disabled={busy || !editable}
        onClick={() => void perform(route, {mode: 'geometry', edit: {
          component_id: patch.target_component_id, geometry: patch.payload.geometry,
        }})}>Send geometry for review</button>
      {!editable && <small>Make one geometry edit to a component to request review.</small>}
    </div>
    {runs.map(run => {
      const current = run.revision_id === garment.draft_revision_id;
      const pending = run.status === 'awaiting_review';
      const decide = (decision: string) => perform(`${route}/${run.id}/decision`, {
        checkpoint_digest: run.checkpoint_digest, decision,
      });
      return <article className="reference-card" key={run.id}>
        <h3>{run.mode === 'concept' ? 'Fixture concept' : 'Geometry review'}</h3>
        <p>{run.status.replaceAll('_', ' ')} · {current ? 'Current revision' : 'Earlier revision'}</p>
        {run.result.thumbnail_jpeg && <Image src={`data:image/jpeg;base64,${run.result.thumbnail_jpeg}`}
          alt="Offline garment concept" width={320} height={200} unoptimized
          style={{width: '100%', height: 'auto'}}/>}
        {run.result.operations?.map(operation => <p key={operation.target_component_id}>
          {operation.target_component_id} · geometry update
        </p>)}
        {pending && run.created_by_viewer && <button className="button secondary" disabled={busy}
          onClick={() => void decide('cancel')}>Cancel review request</button>}
        {pending && !run.created_by_viewer && <div className="compact-form">
          <button className="button primary" disabled={busy || !current}
            onClick={() => void decide('approve')}>Approve review</button>
          <button className="button secondary" disabled={busy}
            onClick={() => void decide('reject')}>Reject review</button>
        </div>}
        {run.proposal_id && current && <button className="button secondary" disabled={busy || !!changes.length}
          onClick={() => void onOpenProposal(run.proposal_id!, run.result.operations || [])}>Open reviewed patch</button>}
      </article>;
    })}
  </section>;
}
