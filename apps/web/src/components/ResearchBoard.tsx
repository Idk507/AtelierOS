'use client';

import { useEffect, useState, type FormEvent } from 'react';
import Image from 'next/image';
import { api } from '@/lib/api';
import type { Garment } from '@/lib/types';

interface Source { id: string; title: string; excerpt: string; rights: string; url: string | null; thumbnail_jpeg?: string }
interface Brief { id: string; question: string; revision_id: string; cards: {source_id: string; title: string; excerpt: string}[] }
interface Board { sources: Source[]; briefs: Brief[] }
interface SearchHit { title: string; url: string; published_date: string | null }

export function ResearchBoard({garment}: {garment: Garment}) {
  const route = `/garments/${garment.id}/research`;
  const [board, setBoard] = useState<Board | null>(null);
  const [selection, setSelection] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [capabilities, setCapabilities] = useState({search: false, capture: false});
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  useEffect(() => {
    let active = true;
    void api<Board>(route).then(data => { if (active) setBoard(data); })
      .catch(() => { if (active) setError('Could not open the research board.'); });
    void api<typeof capabilities>(`${route}/capabilities`)
      .then(data => { if (active) setCapabilities(data); }).catch(() => {});
    return () => { active = false; };
  }, [route]);

  async function searchSources(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      const result = await api<{results: SearchHit[]}>(`${route}/search`, {
        base_revision: garment.draft_revision_id, query: data.get('query'),
        geography: data.get('geography'), period: data.get('period') || null,
      });
      setHits(result.results);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Search failed.'); }
    finally { setBusy(false); }
  }

  async function capture(hit: SearchHit) {
    setBusy(true); setError('');
    try {
      await api(`${route}/capture`, {base_revision: garment.draft_revision_id,
        title: hit.title.slice(0, 200), url: hit.url});
      setBoard(await api<Board>(route));
      setHits(current => current?.filter(result => result.url !== hit.url) ?? null);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Capture failed.'); }
    finally { setBusy(false); }
  }

  async function addImage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get('image');
    if (!(file instanceof File) || file.size === 0 || file.size > 256000) {
      setError('Choose a JPEG image under 256 KB.');
      return;
    }
    setBusy(true); setError('');
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = '';
      for (const byte of bytes) binary += String.fromCharCode(byte);
      await api(`${route}/images`, {base_revision: garment.draft_revision_id,
        title: data.get('title'), caption: data.get('caption'), rights: data.get('rights'),
        image_base64: btoa(binary)});
      setBoard(await api<Board>(route));
      form.reset();
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Image could not be saved.'); }
    finally { setBusy(false); }
  }

  async function submit(event: FormEvent<HTMLFormElement>, brief: boolean) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true); setError('');
    try {
      const base_revision = garment.draft_revision_id;
      if (brief) await api(`${route}/briefs`, {base_revision, question: data.get('question'), source_ids: selection});
      else await api(`${route}/sources`, {base_revision, title: data.get('title'), excerpt: data.get('excerpt'),
        rights: data.get('rights'), url: data.get('url') || null});
      setBoard(await api<Board>(route));
      form.reset();
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Research could not be saved.'); }
    finally { setBusy(false); }
  }

  return <section className="inspector-section research-board" aria-label="Research board">
    <p className="eyebrow">CITED REFERENCES</p><h2>Research board</h2>
    <p className="muted">Save excerpts from your notes and sources. Select reusable excerpts to build a cited brief.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {!board && !error && <p role="status">Loading references…</p>}
    {capabilities.search && <form className="compact-form" onSubmit={searchSources}>
      <label htmlFor="web-research-query">Public web search</label>
      <input id="web-research-query" name="query" required maxLength={300}/>
      <label htmlFor="web-research-geography">Geography (optional)</label>
      <input id="web-research-geography" name="geography" maxLength={80}/>
      <label htmlFor="web-research-period">Published</label>
      <select id="web-research-period" name="period"><option value="">Any date</option>
        <option value="week">Past week</option><option value="month">Past month</option>
        <option value="year">Past year</option></select>
      <p className="muted">Search sends these fields to Tavily. Keep client details out of the query.</p>
      <button className="button secondary" disabled={busy}>Find sources</button>
    </form>}
    {hits?.length === 0 && <p className="muted">No more results to review.</p>}
    {hits?.map(hit => <article className="reference-card" key={hit.url}>
      <a href={hit.url} target="_blank" rel="noopener noreferrer">{hit.title} ↗</a>
      <small>{hit.published_date || 'Publication date unknown'}</small>
      {capabilities.capture && <button className="button secondary" disabled={busy}
        onClick={() => void capture(hit)}>Save reference snapshot</button>}
    </article>)}
    <form className="compact-form" onSubmit={event => void submit(event, false)}>
      <label htmlFor="source-title">Source title</label><input id="source-title" name="title" required maxLength={200}/>
      <label htmlFor="source-excerpt">Source excerpt</label><textarea id="source-excerpt" name="excerpt" required maxLength={4000} rows={4}/>
      <label htmlFor="source-url">Citation URL (optional)</label><input id="source-url" name="url" type="url" maxLength={2048}/>
      <label htmlFor="source-rights">Reuse rights</label><select id="source-rights" name="rights" defaultValue="reference_only">
        <option value="reference_only">Reference only</option><option value="owned">Studio owns this text</option><option value="licensed">Licensed for reuse</option>
      </select><button className="button secondary" disabled={busy}>Save source</button>
    </form>
    <details><summary>Add a moodboard image</summary>
      <form className="compact-form" onSubmit={addImage}>
        <p className="muted">Choose a JPEG under 256 KB that your studio owns or can reuse. The board keeps a thumbnail.</p>
        <label htmlFor="moodboard-image">JPEG image</label><input id="moodboard-image" name="image" type="file" accept="image/jpeg" required/>
        <label htmlFor="moodboard-title">Image title</label><input id="moodboard-title" name="title" required maxLength={200}/>
        <label htmlFor="moodboard-caption">Image description</label><input id="moodboard-caption" name="caption" required maxLength={500}/>
        <label htmlFor="moodboard-rights">Image reuse rights</label><select id="moodboard-rights" name="rights" required defaultValue="">
          <option value="" disabled>Select rights</option><option value="owned">Studio owns this image</option><option value="licensed">Licensed for reuse</option>
        </select><button className="button secondary" disabled={busy}>Save moodboard image</button>
      </form>
    </details>
    {board?.sources.map(source => <article className="reference-card" key={source.id}>
      <label><input type="checkbox" checked={selection.includes(source.id)} disabled={source.rights === 'reference_only'}
        onChange={event => setSelection(list => event.target.checked ? [...list,source.id] : list.filter(id => id !== source.id))}/>{source.title}</label>
      {source.thumbnail_jpeg && <Image src={`data:image/jpeg;base64,${source.thumbnail_jpeg}`}
        width={320} height={320} alt={source.excerpt} unoptimized style={{width: '100%', height: 'auto'}}/>}
      <p>{source.excerpt}</p><small>{source.rights.replaceAll('_', ' ')}</small>
      {source.url && <a href={source.url} target="_blank" rel="noopener noreferrer">Open citation ↗</a>}
    </article>)}
    {!!board?.sources.length && <form className="compact-form" onSubmit={event => void submit(event, true)}>
      <label htmlFor="research-question">Research question</label><input id="research-question" name="question" required maxLength={500}/>
      <button className="button primary" disabled={busy || !selection.length || selection.length > 12}>Build cited brief</button>
    </form>}
    {board?.briefs.map(brief => <article className="reference-card" key={brief.id}>
      <h3>{brief.question}</h3><small>Revision {brief.revision_id.slice(0,8)}</small>
      {brief.cards.map(card => <blockquote key={card.source_id}><p>{card.excerpt}</p><cite>{card.title}</cite></blockquote>)}
    </article>)}
  </section>;
}
