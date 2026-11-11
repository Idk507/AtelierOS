'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { api } from '@/lib/api';
import type { Garment } from '@/lib/types';

interface Offer {id: string; name: string; evidence: string; currency: string;
  total: string | null; compatibility: 'compatible' | 'incompatible' | 'unknown';
  composition?: string; width_cm?: number; gsm?: number; observed_on?: string}

export function MaterialsBoard({garment, disabled, onPropose}: {
  garment: Garment; disabled: boolean; onPropose: (comparisonId: string, offerId: string) => Promise<void>;
}) {
  const route = `/garments/${garment.id}/materials`;
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [comparisonId, setComparisonId] = useState('');
  const [catalog, setCatalog] = useState<{id: string; name: string; supersedes_offer_id?: string}[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    void api<typeof catalog>(route).then(rows => {if (active) setCatalog(rows);})
      .catch(() => {if (active) setError('Could not load the existing catalog.');});
    return () => {active = false;};
  }, [route]);

  const retired = new Set(catalog.map(offer => offer.supersedes_offer_id));

  async function submit(event: FormEvent<HTMLFormElement>, comparison: boolean) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const base_revision = garment.draft_revision_id;
    const currency = data.get('currency');
    setBusy(true); setError(''); setNotice('');
    try {
      if (comparison) {
        const width = data.get('minimum-width');
        const gsm = data.get('maximum-gsm');
        const result = await api<{id: string; offers: Offer[]}>(`${route}/compare`, {base_revision, currency,
          length_metres: data.get('length'), trim_cost: data.get('trim'), other_cost: data.get('other'),
          waste_percent: Number(data.get('waste')), minimum_stretch_percent: Number(data.get('minimum')),
          minimum_width_cm: width ? Number(width) : null, maximum_gsm: gsm ? Number(gsm) : null});
        setOffers(result.offers);
        setComparisonId(result.id);
      } else {
        const stretch = data.get('stretch');
        const available = data.get('available');
        const width = data.get('width');
        const gsm = data.get('gsm');
        const offer = await api<(typeof catalog)[number]>(`${route}/offers`, {base_revision, currency, name: data.get('name'),
          evidence: data.get('evidence'), price_per_metre: data.get('price'),
          stretch_percent: stretch ? Number(stretch) : null,
          width_cm: width ? Number(width) : null, gsm: gsm ? Number(gsm) : null,
          composition: data.get('composition') || null, observed_on: data.get('observed-on') || null,
          supersedes_offer_id: data.get('supersedes') || null,
          available: available === 'yes' ? true : available === 'no' ? false : null});
        setCatalog(rows => [offer, ...rows].slice(0,50));
        setOffers(null);
        setNotice('Offer saved. Run a comparison to review the costs.');
        form.reset();
      }
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Material details could not be saved.'); }
    finally { setBusy(false); }
  }

  async function importCatalog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get('catalog');
    if (!(file instanceof File) || !file.size || file.size > 60000) {
      setError('Choose a CSV file under 60 KB.');
      return;
    }
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await api<{imported: number}>(`${route}/import`, {
        base_revision: garment.draft_revision_id, csv_text: await file.text(),
      });
      setOffers(null);
      setCatalog(await api<typeof catalog>(route));
      setNotice(`Imported ${result.imported} offers. Run a comparison to review them.`);
      form.reset();
    } catch (failure) {setError(failure instanceof Error ? failure.message : 'Catalog import failed.');}
    finally {setBusy(false);}
  }

  function currencies() {
    return ['INR', 'USD', 'EUR', 'GBP'].map(currency => <option key={currency}>{currency}</option>);
  }

  return <section className="inspector-section research-board" aria-label="Material alternatives">
    <p className="eyebrow">SOURCING &amp; COST</p><h2>Material alternatives</h2>
    <p className="muted">Compare studio-recorded offers. Keep evidence with each price and availability statement.</p>
    {notice && <p role="status">{notice}</p>}{error && <p role="alert" className="error">{error}</p>}
    <details><summary>Record an offer</summary><form className="compact-form" onSubmit={event => void submit(event,false)}>
      <label>Material name<input name="name" required maxLength={120}/></label>
      <label>Supplier evidence<textarea name="evidence" required maxLength={1000}/></label>
      <label>Price per metre<input name="price" inputMode="decimal" required/></label>
      <label>Offer currency<select name="currency">{currencies()}</select></label>
      <label>Measured stretch (%)<input name="stretch" type="number" min={0} max={300}/></label>
      <label>Measured width (cm)<input name="width" type="number" min={1} max={500}/></label>
      <label>Measured weight (GSM)<input name="gsm" type="number" min={1} max={2000}/></label>
      <label>Composition<input name="composition" maxLength={120}/></label>
      <label>Observed on<input name="observed-on" type="date"/></label>
      {catalog.length > 0 && <label>Replace previous offer<select name="supersedes">
        <option value="">New offer</option>
        {catalog.filter(offer => !retired.has(offer.id)).map(offer => <option value={offer.id} key={offer.id}>{offer.name}</option>)}
      </select></label>}
      <label htmlFor="offer-availability">Availability</label>
      <select id="offer-availability" name="available"><option value="unknown">Unknown</option><option value="yes">Available</option><option value="no">Unavailable</option></select>
      <button className="button secondary" disabled={busy || disabled}>Save offer</button>
    </form></details>
    <details><summary>Import supplier catalog</summary>
      <form className="compact-form" onSubmit={importCatalog}>
        <p className="muted">CSV columns: name, evidence, price_per_metre, currency, observed_on. Add measured width, stretch, or GSM when supplied.</p>
        <label htmlFor="catalog-csv">Catalog CSV</label><input id="catalog-csv" name="catalog" type="file" accept=".csv,text/csv" required/>
        <button className="button secondary" disabled={busy || disabled}>Import offers</button>
      </form>
    </details>
    <form className="compact-form" onSubmit={event => void submit(event,true)}>
      <label>Required length (m)<input name="length" inputMode="decimal" required/></label>
      <label>Minimum stretch (%)<input name="minimum" type="number" min={0} max={300} defaultValue={0} required/></label>
      <label>Minimum width (cm, optional)<input name="minimum-width" type="number" min={1} max={500}/></label>
      <label>Maximum weight (GSM, optional)<input name="maximum-gsm" type="number" min={1} max={2000}/></label>
      <label>Waste allowance (%)<input name="waste" type="number" min={0} max={100} defaultValue={10} required/></label>
      <label>Trim cost<input name="trim" inputMode="decimal" defaultValue="0" required/></label>
      <label>Other cost<input name="other" inputMode="decimal" defaultValue="0" required/></label>
      <label>Estimate currency<select name="currency">{currencies()}</select></label>
      <button className="button primary" disabled={busy || disabled}>Compare materials</button>
    </form>
    {offers?.length === 0 && <p className="muted">Record a material offer to start a comparison.</p>}
    {offers?.map(offer => <article key={offer.id} className="reference-card">
      <h3>{offer.name}</h3><p>{offer.compatibility} · {offer.total ? `${offer.currency} ${offer.total}` : 'Currency differs'}</p>
      <p>{offer.evidence}</p>
      {offer.composition && <p>{offer.composition}</p>}
      <p>{offer.width_cm ? `${offer.width_cm} cm` : 'Width unknown'} · {offer.gsm ? `${offer.gsm} GSM` : 'Weight unknown'}</p>
      {offer.observed_on && <small>Observed {offer.observed_on}</small>}
      <button className="button secondary" disabled={disabled || busy || !offer.total || offer.compatibility !== 'compatible' || garment.design.material_id === offer.id}
        onClick={() => void onPropose(comparisonId, offer.id)}>Review substitution</button>
    </article>)}
    {!!offers?.length && <p className="muted">Estimates exclude tax, shipping and currency conversion.</p>}
  </section>;
}
