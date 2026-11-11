'use client';

import { useEffect, useState, type FormEvent } from 'react';
import Image from 'next/image';
import { api, ApiError } from '@/lib/api';
import type { Garment, SampleFinding, SampleMeasurement } from '@/lib/types';

export function SampleFeedback({garment, disabled}: {garment: Garment; disabled: boolean}) {
  const route = `/garments/${garment.id}/samples`;
  const [findings, setFindings] = useState<SampleFinding[]>([]);
  const [capabilities, setCapabilities] = useState({can_record: false, can_resolve: false});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [filter, setFilter] = useState<'all' | 'open' | 'resolved' | 'blocking'>('all');
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [annotationX, setAnnotationX] = useState('');
  const [annotationY, setAnnotationY] = useState('');
  useEffect(() => {
    if (!photo) {setPreview(''); return;}
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);
  useEffect(() => {
    let active = true;
    void Promise.all([api<SampleFinding[]>(route), api<typeof capabilities>(`${route}/capabilities`)])
      .then(([rows, access]) => {if (active) {setFindings(rows); setCapabilities(access);}})
      .catch(() => {if (active) setError('Could not load sample feedback.');});
    return () => {active = false;};
  }, [route]);

  function failure(error: unknown) {
    if (error instanceof ApiError && error.code === 'stale_revision') return 'A newer revision exists. Reload the garment before recording feedback.';
    if (error instanceof ApiError && error.status === 403) return 'Your role no longer permits this action.';
    return error instanceof Error ? error.message : 'Could not save sample feedback.';
  }

  const visibleFindings = findings.filter(finding => {
    if (filter === 'open') return !finding.resolution;
    if (filter === 'resolved') return !!finding.resolution;
    if (filter === 'blocking') return finding.severity === 'blocking';
    return true;
  });

  async function record(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true); setError(''); setNotice('');
    try {
      let photo_jpeg: string | null = null;
      const file = data.get('photo');
      if (file instanceof File && file.size) {
        if (file.type !== 'image/jpeg' || file.size > 256000) throw new Error('Choose a JPEG under 256 KB.');
        if (!data.get('rights')) throw new Error('Confirm your rights to use this photo.');
        let binary = '';
        for (const byte of new Uint8Array(await file.arrayBuffer())) binary += String.fromCharCode(byte);
        photo_jpeg = btoa(binary);
      }
      const measured = String(data.get('value') || '').trim();
      const measurement: SampleMeasurement | null = measured ? {
        label: String(data.get('measurement_label')), value: measured,
        unit: String(data.get('unit')) as SampleMeasurement['unit'], source: String(data.get('source')),
      } : null;
      const x = String(data.get('x') || '');
      const y = String(data.get('y') || '');
      if ((x || y) && (!photo_jpeg || !x || !y)) throw new Error('A photo annotation needs a photo and both coordinates.');
      await api(route, {base_revision: garment.draft_revision_id,
        sample_label: data.get('sample_label'), component_id: data.get('component') || null,
        observation: data.get('observation'), severity: data.get('severity'), measurement,
        photo_jpeg, photo_rights_confirmed: !!data.get('rights'),
        annotation: x && y ? {x: Number(x), y: Number(y)} : null});
      setFindings(await api<SampleFinding[]>(route)); form.reset();
      setPhoto(null); setAnnotationX(''); setAnnotationY('');
      setNotice('Feedback recorded for this revision. Earlier handoff evidence may need review.');
    } catch (error) {setError(failure(error));} finally {setBusy(false);}
  }

  async function resolve(event: FormEvent<HTMLFormElement>, finding: SampleFinding) {
    event.preventDefault(); const form = event.currentTarget;
    setBusy(true); setError(''); setNotice('');
    try {
      await api(`${route}/${finding.id}/resolve`, {base_revision: garment.draft_revision_id,
        resolution: new FormData(form).get('resolution')});
      setFindings(await api<SampleFinding[]>(route));
      setNotice('Resolution recorded. Refresh the technical review before preparing a new handoff.');
    } catch (error) {setError(failure(error));} finally {setBusy(false);}
  }

  return <section className="inspector-section">
    <p className="eyebrow">PHYSICAL SAMPLE REVIEW</p><h2>Sample feedback</h2>
    <p className="muted">Revision {garment.draft_revision_id.slice(0,8)}. Record observed measurements and their source. Technical adequacy requires professional review.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="success" role="status">{notice}</p>}
    {capabilities.can_record && <form className="compact-form" onSubmit={record}>
      <fieldset disabled={disabled || busy}>
        <label>Sample label<input name="sample_label" required maxLength={100}/></label>
        <label>Component<select name="component"><option value="">Whole garment</option>{garment.design.components.map(c => <option key={c.id} value={c.id}>{c.id}</option>)}</select></label>
        <label>Observation<textarea name="observation" required maxLength={1000}/></label>
        <label>Severity<select name="severity"><option value="note">Note</option><option value="blocking">Blocks handoff</option></select></label>
        <details><summary>Optional measured evidence</summary>
          <label>Measurement name<input name="measurement_label" maxLength={100}/></label>
          <label>Measured value<input name="value" inputMode="decimal" pattern="[0-9]+(\.[0-9]{1,3})?"/></label>
          <label>Unit<select name="unit"><option>cm</option><option>mm</option><option>in</option></select></label>
          <label>Measurement source<input name="source" maxLength={300} placeholder="Who measured it and how"/></label>
        </details>
        <details><summary>Optional sample photo</summary>
          <label>JPEG photo, up to 256 KB<input type="file" name="photo" accept="image/jpeg" onChange={event => {
            const selected = event.currentTarget.files?.[0] || null;
            setAnnotationX(''); setAnnotationY('');
            if (selected && (selected.type !== 'image/jpeg' || selected.size > 256000)) {
              setPhoto(null); setError('Choose a JPEG under 256 KB.'); event.currentTarget.value = ''; return;
            }
            setPhoto(selected); setError('');
          }}/></label>
          <label><input type="checkbox" name="rights"/>I have rights to use this sample photo.</label>
          {preview && <>
            <p id="sample-annotation-help" className="muted">Click or tap the photo to place a marker. With the photo focused, use arrow keys to move it; hold Shift for larger steps. You can also enter coordinates below.</p>
            <button type="button" aria-label="Place sample photo annotation" aria-describedby="sample-annotation-help"
              style={{position: 'relative', display: 'block', width: '100%', maxWidth: 320, padding: 0, border: '1px solid currentColor', background: 'transparent', cursor: 'crosshair'}}
              onClick={event => {
                // Keyboard activation starts at the centre; pointer coordinates use the displayed image.
                const bounds = event.currentTarget.getBoundingClientRect();
                const coordinate = (value: number) => String(Math.max(0, Math.min(1000, Math.round(value))));
                setAnnotationX(event.detail === 0 ? '500' : coordinate((event.clientX - bounds.left) / bounds.width * 1000));
                setAnnotationY(event.detail === 0 ? '500' : coordinate((event.clientY - bounds.top) / bounds.height * 1000));
              }}
              onKeyDown={event => {
                if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
                event.preventDefault();
                const step = event.shiftKey ? 50 : 10;
                const x = annotationX === '' ? 500 : Number(annotationX);
                const y = annotationY === '' ? 500 : Number(annotationY);
                setAnnotationX(String(Math.max(0, Math.min(1000, x + (event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0)))));
                setAnnotationY(String(Math.max(0, Math.min(1000, y + (event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0)))));
              }}>
              <Image src={preview} alt="Selected sample photo" width={320} height={320} unoptimized style={{display: 'block', width: '100%', height: 'auto', pointerEvents: 'none'}}/>
              {annotationX !== '' && annotationY !== '' && <span aria-hidden="true" style={{position: 'absolute', left: `${Number(annotationX) / 10}%`, top: `${Number(annotationY) / 10}%`, color: '#b00020', background: 'white', borderRadius: '50%', transform: 'translate(-50%, -50%)', lineHeight: 1}}>⊕</span>}
            </button>
            <p role="status" className="muted">{annotationX !== '' && annotationY !== '' ? `Marker: ${annotationX}, ${annotationY}` : 'No marker placed.'}</p>
            <button type="button" className="button secondary" onClick={() => {setAnnotationX(''); setAnnotationY('');}}>Clear marker</button>
          </>}
          <p className="muted">Optional location: 0 is the left/top edge, 1000 is the right/bottom edge.</p>
          <label>Horizontal position<input type="number" name="x" min={0} max={1000} step={1} value={annotationX} onChange={event => setAnnotationX(event.currentTarget.value)}/></label>
          <label>Vertical position<input type="number" name="y" min={0} max={1000} step={1} value={annotationY} onChange={event => setAnnotationY(event.currentTarget.value)}/></label>
        </details>
        <button className="button secondary" type="submit">Record sample finding</button>
      </fieldset>
    </form>}
    {!findings.length && <p className="muted">No feedback recorded for this revision.</p>}
    {!!findings.length && <label>Show findings<select value={filter} onChange={event => setFilter(event.currentTarget.value as typeof filter)}>
      <option value="all">All ({findings.length})</option>
      <option value="open">Open ({findings.filter(row => !row.resolution).length})</option>
      <option value="resolved">Resolved ({findings.filter(row => !!row.resolution).length})</option>
      <option value="blocking">Blocking ({findings.filter(row => row.severity === 'blocking').length})</option>
    </select></label>}
    {!visibleFindings.length && !!findings.length && <p className="muted">No findings match this filter.</p>}
    {visibleFindings.map(finding => <article className="reference-card" key={finding.id}>
      <h3>{finding.sample_label}</h3><p>{finding.severity === 'blocking' ? 'Blocking finding' : 'Review note'} · {finding.component_id || 'Whole garment'}</p>
      <p>{finding.observation}</p>
      <small>Recorded by {finding.recorded_by} · {new Date(finding.recorded_at).toLocaleString()}</small>
      {finding.measurement && <p>{finding.measurement.label}: {finding.measurement.value} {finding.measurement.unit}<br/><small>Source: {finding.measurement.source}</small></p>}
      {finding.thumbnail_jpeg && <div style={{position: 'relative', width: 160}}><Image src={`data:image/jpeg;base64,${finding.thumbnail_jpeg}`} alt={`Sample evidence for ${finding.sample_label}`} width={160} height={160} unoptimized style={{display: 'block', width: '100%', height: 'auto'}}/>
        {finding.annotation && <span role="img" aria-label={`Annotated location ${finding.annotation.x}, ${finding.annotation.y}`} style={{position: 'absolute', left: `${finding.annotation.x / 10}%`, top: `${finding.annotation.y / 10}%`, color: '#b00020', transform: 'translate(-50%, -50%)'}}>⊕</span>}</div>}
      {finding.resolution ? <p>Resolution: {finding.resolution.note}<br/><small>By {finding.resolution.by} · {new Date(finding.resolution.at).toLocaleString()}</small></p>
        : capabilities.can_resolve && <form className="compact-form" onSubmit={event => void resolve(event, finding)}>
          <label>Patternmaker resolution<textarea name="resolution" required maxLength={1000} disabled={disabled || busy}/></label>
          <button className="button secondary" disabled={disabled || busy}>Record resolution</button>
        </form>}
    </article>)}
  </section>;
}
