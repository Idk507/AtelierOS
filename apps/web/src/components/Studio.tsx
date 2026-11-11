'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { diffDesigns, initialDesign } from '@/lib/design';
import type { AuditEvent, Design, Garment, GarmentSummary, Patch, Project } from '@/lib/types';
import { ResearchBoard } from './ResearchBoard';
import { MaterialsBoard } from './MaterialsBoard';
import { HandoffDrafts } from './HandoffDrafts';
import { WorkflowPanel } from './WorkflowPanel';
import { SampleFeedback } from './SampleFeedback';

const Canvas = dynamic(() => import('./GarmentCanvas').then(m => m.GarmentCanvas), {ssr: false,
  loading: () => <div className="canvas-loading" role="status">Opening your drawing surface…</div>});

function explanation(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Your session has ended. Sign in again to continue.';
    if (error.code === 'stale_revision') return 'This design has a newer revision. Reload before applying your changes.';
    if (error.code === 'locked_component') return 'A locked component would change. Request an authorized unlock first.';
    if (error.status === 403) return 'Your role does not allow this action.';
    return error.message;
  }
  return 'The workspace could not complete this action. Your saved revisions are safe.';
}

export function Studio({subject}: {subject: string}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState('');
  const [garments, setGarments] = useState<GarmentSummary[]>([]);
  const [garment, setGarment] = useState<Garment | null>(null);
  const [draft, setDraft] = useState<Design | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [history, setHistory] = useState<AuditEvent[]>([]);
  const [review, setReview] = useState<{id: string; operations: Patch[]; impact?: {id: string; kind: string}[]; estimate?: string} | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [panel, setPanel] = useState<'components' | 'history' | 'research' | 'materials' | 'reviews' | 'samples'>('components');
  const [projectName, setProjectName] = useState('');
  const [garmentName, setGarmentName] = useState('');
  const [unlockId, setUnlockId] = useState('');
  const loadSequence = useRef(0);
  const changes = garment && draft ? diffDesigns(garment.design, draft) : [];
  const component = draft?.components.find(c => c.id === selected);

  async function action(fn: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); } catch (e) { setError(explanation(e)); }
    finally { setBusy(false); }
  }

  async function openGarment(id: string) {
    const sequence = ++loadSequence.current;
    const [record, events] = await Promise.all([api<Garment>(`/garments/${id}`), api<AuditEvent[]>(`/garments/${id}/audit`)]);
    if (sequence !== loadSequence.current) return;
    setGarment(record); setDraft(record.design); setHistory(events); setReview(null); setSelected(null);
    setGarments(list => list.map(g => g.id === record.id ? {...g,
      draft_revision_id: record.draft_revision_id, approved_revision_id: record.approved_revision_id} : g));
    const url = new URL(window.location.href);
    url.searchParams.set('project', record.project_id); url.searchParams.set('garment', id);
    window.history.replaceState(null, '', url);
  }

  async function openProject(id: string, restore?: string) {
    const sequence = ++loadSequence.current;
    const list = await api<GarmentSummary[]>(`/projects/${id}/garments`);
    if (sequence !== loadSequence.current) return;
    setProjectId(id); setGarments(list); setGarment(null); setDraft(null); setReview(null);
    if (restore && list.some(g => g.id === restore)) await openGarment(restore);
    else if (list.length) await openGarment(list[0].id);
  }

  useEffect(() => {
    let active = true;
    const sequence = ++loadSequence.current;
    async function load() {
      try {
        const list = await api<Project[]>('/projects');
        if (!active) return;
        setProjects(list);
        const query = new URLSearchParams(window.location.search);
        const project = list.find(p => p.id === query.get('project')) || list[0];
        if (project) {
          const list = await api<GarmentSummary[]>(`/projects/${project.id}/garments`);
          if (!active || sequence !== loadSequence.current) return;
          setProjectId(project.id); setGarments(list);
          const chosen = list.find(g => g.id === query.get('garment')) || list[0];
          if (chosen) {
            const [record, events] = await Promise.all([api<Garment>(`/garments/${chosen.id}`),api<AuditEvent[]>(`/garments/${chosen.id}/audit`)]);
            if (!active || sequence !== loadSequence.current) return;
            setGarment(record); setDraft(record.design); setHistory(events);
          }
        }
      } catch (e) { if (active) setError(explanation(e)); }
      finally {if (active) setBusy(false);}
    }
    void load();
    return () => { active = false; };
  }, []);

  async function createProject(event: React.FormEvent) {
    event.preventDefault();
    await action(async () => {
      const project = await api<Project>('/projects', {name: projectName.trim()});
      setProjects(old => [...old, project]); setProjectName(''); await openProject(project.id);
      setNotice('Project created. Add your first garment.');
    });
  }

  async function createGarment(event: React.FormEvent) {
    event.preventDefault();
    await action(async () => {
      const record = await api<{id: string}>(`/projects/${projectId}/garments`,
        {name: garmentName.trim(), design: initialDesign()});
      const list = await api<GarmentSummary[]>(`/projects/${projectId}/garments`);
      setGarments(list); setGarmentName(''); await openGarment(record.id);
      setNotice('An editable starting sketch. No technical details are implied.');
    });
  }

  async function reviewChanges(target = draft) {
    if (!garment || !target) return;
    await action(async () => {
      const operations = diffDesigns(garment.design, target);
      if (!operations.length) { setNotice('No changes to review.'); return; }
      const proposal = await api<{id: string}>(`/garments/${garment.id}/patch-proposals`,
        {base_revision: garment.draft_revision_id, operations, justification: 'Designer-reviewed canvas edit'});
      const preview = await api<{design: Design}>(`/garments/${garment.id}/patch-proposals/${proposal.id}/preview`);
      setDraft(preview.design); setReview({id: proposal.id, operations});
    });
  }

  async function commit() {
    if (!garment || !review) return;
    await action(async () => {
      await api(`/garments/${garment.id}/patch-proposals/${review.id}/accept`, {base_revision: garment.draft_revision_id});
      await openGarment(garment.id); setNotice('New draft saved. Approval remains a separate decision.');
    });
  }

  async function addLock() {
    if (!garment || !component || changes.length) return;
    await action(async () => {
      await api(`/garments/${garment.id}/constraints`, {base_revision: garment.draft_revision_id, component_id: component.id, kind: 'hard_lock'});
      await openGarment(garment.id); setNotice('Component locked in a new draft revision.');
    });
  }

  async function requestUnlock() {
    if (!garment || !component) return;
    await action(async () => {
      const result = await api<{id: string}>(`/garments/${garment.id}/unlock-requests`,
        {base_revision: garment.draft_revision_id, component_id: component.id, reason: 'Designer requests a component revision'});
      setUnlockId(result.id); setNotice('Unlock requested. A different organization administrator must authorize it.');
    });
  }

  async function approve() {
    if (!garment || changes.length) return;
    await action(async () => {
      await api(`/garments/${garment.id}/approvals`, {base_revision: garment.draft_revision_id,
        revision_id: garment.draft_revision_id, content_hash: garment.content_hash, purpose: 'aesthetic', decision: 'approve'});
      await openGarment(garment.id); setNotice('Aesthetic approval recorded for this exact revision.');
    });
  }

  const revisionEvents = history.filter(e => e.event_type === 'design.revision.created');
  return <div className="studio-shell">
    <header className="studio-header"><Link className="wordmark" href="/">Atelier<span>OS</span><i /></Link>
      <div className="workspace-label">DESIGN WORKSPACE <span>/</span> {projects.find(p => p.id === projectId)?.name || 'Your studio'}</div>
      <div className="account"><span title={subject}>{subject}</span><button className="text-button" onClick={() => void action(async () => {
        const response = await fetch('/auth/logout', {method: 'POST', credentials: 'same-origin'});
        if (!response.ok) throw new Error('Sign-out failed');
        window.location.replace('/');
      })}>Sign out</button></div>
    </header>
    <aside className="project-rail">
      <div className="rail-title"><span className="eyebrow">STUDIO LIBRARY</span><span className="count">{projects.length}</span></div>
      <label className="field-label" htmlFor="project">Project</label>
      <select id="project" value={projectId} disabled={busy || changes.length > 0 || !!review} onChange={e => void action(() => openProject(e.target.value))}>
        <option value="" disabled>Select a project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
      <div className="garment-list" aria-label="Garments">{garments.map(g => <button key={g.id}
        className={garment?.id === g.id ? 'garment-row active' : 'garment-row'}
        disabled={busy || changes.length > 0 || !!review} onClick={() => void action(() => openGarment(g.id))}>
        <span className="garment-icon" aria-hidden>♧</span><span>{g.name}<small>{g.approved_revision_id === g.draft_revision_id ? 'Aesthetic approved' : 'Draft in progress'}</small></span></button>)}</div>
      {projectId && <form onSubmit={createGarment} className="compact-form"><label htmlFor="garment-name">Add a garment</label>
        <input id="garment-name" placeholder="e.g. Festive blouse" value={garmentName} onChange={e => setGarmentName(e.target.value)} maxLength={200} required />
        <button className="button secondary" disabled={busy || !garmentName.trim() || changes.length > 0}>＋ Create garment</button></form>}
      <details className="project-create"><summary>New project</summary><form onSubmit={createProject} className="compact-form">
        <label htmlFor="project-name">Project name</label><input id="project-name" value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="A collection or commission" maxLength={200} required />
        <button className="button secondary" disabled={busy || !projectName.trim()}>Create project</button></form></details>
      <div className="rail-note"><span className="status-dot" />Designer-controlled<br /><small>Every saved change has a history.</small></div>
    </aside>
    <main className="work-area">
      <div className="canvas-heading"><div><p className="eyebrow">SKETCH / EDITABLE DESIGN</p><h1>{garment?.name || 'Make room for your next idea.'}</h1></div>
        {garment && <span className={garment.approved_revision_id === garment.draft_revision_id ? 'badge approved' : 'badge'}>{garment.approved_revision_id === garment.draft_revision_id ? 'Aesthetic approved' : 'Unapproved draft'}</span>}</div>
      <div className="feedback" aria-live="polite">{error && <p className="error" role="alert">{error} {error.includes('session') && <a href="/auth/login">Sign in</a>}
        {error.includes('newer revision') && garment && <button className="text-button" onClick={() => void action(() => openGarment(garment.id))}>Reload current revision</button>}</p>}
        {notice && <p className="success" role="status">{notice}</p>}</div>
      {garment && draft ? <>
        <div className="canvas-toolbar"><span>{draft.components.length} components <b>·</b> {draft.components.filter(c => c.locked).length} locked</span>
          <div><button className="text-button" disabled={busy || !changes.length || !!review} onClick={() => {setDraft(garment.design); setNotice('Uncommitted changes discarded.');}}>Discard edits</button>
          <button className="button primary" disabled={busy || !changes.length || !!review} onClick={() => void reviewChanges()}>{busy ? 'Working…' : `Review changes${changes.length ? ` (${changes.length})` : ''}`}</button></div></div>
        <div className="canvas-frame"><Canvas key={garment.draft_revision_id + (review ? '-review' : '')}
          design={draft} readonly={busy || !!review} onChange={setDraft} onSelect={setSelected} selected={selected} />
          <div className="canvas-caption">EDITABLE SKETCH <span>Illustration, not a sewing pattern</span></div></div>
        <div className="canvas-bottom"><span className="status-dot" /><span>{changes.length ? 'Uncommitted edits · review to save' : 'All edits saved to this revision'}</span><code>{garment.draft_revision_id.slice(0,8)}</code></div>
      </> : <section className="empty-state"><span className="empty-mark" aria-hidden>✳</span><h2>A new design starts here.</h2>
        <p>{projectId ? 'Add a garment to open an editable starting sketch.' : 'Create your first project to keep your garments, edits and decisions together.'}</p>
        {!projectId && <form onSubmit={createProject}><label htmlFor="first-project">Project name</label><input id="first-project" value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="e.g. Festive commissions" required maxLength={200}/><button className="button primary" disabled={busy || !projectName.trim()}>Create your first project ↗</button></form>}</section>}
    </main>
    <aside className="inspector"><div className="inspector-tabs"><button className={panel === 'components' ? 'selected' : ''} onClick={() => setPanel('components')}>Components</button><button className={panel === 'history' ? 'selected' : ''} onClick={() => setPanel('history')}>History</button>{garment && <><button className={panel === 'research' ? 'selected' : ''} onClick={() => setPanel('research')}>Research</button><button className={panel === 'materials' ? 'selected' : ''} onClick={() => setPanel('materials')}>Materials</button><button className={panel === 'samples' ? 'selected' : ''} onClick={() => setPanel('samples')}>Samples</button><button className={panel === 'reviews' ? 'selected' : ''} onClick={() => setPanel('reviews')}>Reviews</button></>}</div>
      {review ? <section className="review-panel"><p className="eyebrow">CHANGE REVIEW</p><h2>{review.operations.length} proposed edits</h2><p>Review the drawing before saving a new, unapproved revision.</p>
        <ul>{review.operations.map(p => <li key={p.target_component_id}><span>{p.target_component_id}</span><small>{p.op}</small></li>)}</ul>
        {review.estimate && <p>Estimated total {review.estimate}. Construction impacts require patternmaker review.</p>}
        {review.impact?.map(artifact => <p key={artifact.id}>{artifact.kind.replaceAll('_', ' ')} will require review.</p>)}
        <button className="button primary" disabled={busy} onClick={() => void commit()}>Commit draft</button>
        <button className="button secondary" disabled={busy} onClick={() => setReview(null)}>Keep editing</button></section>
      : panel === 'samples' && garment ? <SampleFeedback key={garment.draft_revision_id} garment={garment} disabled={busy || changes.length > 0}/>
      : panel === 'research' && garment ? <ResearchBoard key={garment.id} garment={garment}/>
      : panel === 'materials' && garment ? <MaterialsBoard key={garment.draft_revision_id} garment={garment}
        disabled={busy || changes.length > 0} onPropose={(comparisonId, offerId) => action(async () => {
          const route = `/garments/${garment.id}`;
          const proposal = await api<{id: string; operations: Patch[]; currency: string; estimated_total: string}>(
            `${route}/materials/substitutions`, {base_revision: garment.draft_revision_id,
              comparison_id: comparisonId, offer_id: offerId});
          const preview = await api<{design: Design; artifact_impact: {id: string; kind: string}[]}>(
            `${route}/patch-proposals/${proposal.id}/preview`);
          setDraft(preview.design);
          setReview({id: proposal.id, operations: proposal.operations, impact: preview.artifact_impact,
            estimate: `${proposal.currency} ${proposal.estimated_total}`});
        })}/>
      : panel === 'reviews' && garment ? <WorkflowPanel key={garment.draft_revision_id} garment={garment}
        changes={changes} onOpenProposal={(id, operations) => action(async () => {
          const preview = await api<{design: Design}>(`/garments/${garment.id}/patch-proposals/${id}/preview`);
          setDraft(preview.design);
          setReview({id, operations});
        })}/>
      : panel === 'components' ? <>
        <div className="inspector-section"><p className="eyebrow">SEMANTIC LAYERS</p>{draft?.components.map(c => <button key={c.id}
          className={selected === c.id ? 'component-row selected' : 'component-row'} onClick={() => setSelected(c.id)}>
          <span className="layer-icon" aria-hidden>{c.locked ? '▣' : '◇'}</span><span>{c.id.replaceAll('-', ' ')}<small>{c.kind}</small></span><span className="component-state">{c.locked ? 'Locked' : 'Editable'}</span></button>)}
          {!draft && <p className="muted">Your garment components will appear here.</p>}</div>
        {component && <section className="inspector-section"><p className="eyebrow">SELECTED COMPONENT</p><h2>{component.id.replaceAll('-', ' ')}</h2><p className="muted">{component.locked ? 'Protected from direct and indirect edits.' : 'Edit the selected paths on the canvas.'}</p>
          <button className="button secondary" disabled={busy || changes.length > 0 || !!review} onClick={() => void (component.locked ? requestUnlock() : addLock())}>{component.locked ? 'Request unlock' : 'Lock this component'}</button>
          {unlockId && <small className="request-id">Unlock request: {unlockId}</small>}</section>}
        {garment && <section className="inspector-section approval-section"><p className="eyebrow">HUMAN SIGN-OFF</p><h2>Preserve this direction.</h2><p className="muted">Aesthetic approval records this exact design. It does not certify fit or construction.</p><button className="button secondary" disabled={busy || changes.length > 0 || garment.approved_revision_id === garment.draft_revision_id} onClick={() => void approve()}>Approve aesthetics</button></section>}
        {garment && <HandoffDrafts key={garment.draft_revision_id} garment={garment} disabled={busy || changes.length > 0}/>}
      </> : <section className="inspector-section"><p className="eyebrow">IMMUTABLE REVISIONS</p><p className="muted">Restore earlier geometry as a new draft. Current locks remain protected.</p>
        {revisionEvents.map((event,index) => <div className="history-row" key={event.id}><span className="history-point"/><div><strong>{index === 0 ? 'Current draft' : 'Earlier revision'}</strong><small>{new Date(event.created_at).toLocaleString()}</small><code>{event.revision_id?.slice(0,8)}</code>
          {event.revision_id !== garment?.draft_revision_id && <button className="text-button" disabled={busy || changes.length > 0} onClick={() => void action(async () => {
            const revision = await api<{design: Design}>(`/garments/${garment!.id}/revisions/${event.revision_id}`);
            const operations = diffDesigns(garment!.design, revision.design);
            if (!operations.length) {setNotice('That revision has the same editable geometry.'); return;}
            const proposal = await api<{id: string}>(`/garments/${garment!.id}/patch-proposals`, {base_revision: garment!.draft_revision_id, operations, justification: 'Restore earlier geometry as a new draft'});
            const preview = await api<{design: Design}>(`/garments/${garment!.id}/patch-proposals/${proposal.id}/preview`);
            setDraft(preview.design); setReview({id: proposal.id, operations});
          })}>Review restoration ↗</button>}</div></div>)}</section>}
      <div className="inspector-foot">SOURCE OF TRUTH<br /><span>The garment, not the conversation.</span></div>
    </aside>
  </div>;
}
