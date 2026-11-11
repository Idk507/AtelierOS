import type { Design, Patch } from './types';

export function initialDesign(): Design {
  return {material_id: null, components: [
    {id: 'bodice', kind: 'bodice', parent_id: null, locked: false,
      geometry: [230,150,200,190,210,350,390,350,400,190,370,150]},
    {id: 'neckline', kind: 'neckline', parent_id: null, locked: false,
      geometry: [230,150,250,190,275,210,300,216,325,210,350,190,370,150]},
    {id: 'sleeve-left', kind: 'sleeve', parent_id: null, locked: false,
      geometry: [230,150,180,162,120,260,172,284,200,220]},
    {id: 'sleeve-right', kind: 'sleeve', parent_id: null, locked: false,
      geometry: [370,150,420,162,480,260,428,284,400,220]},
    {id: 'hem', kind: 'hem', parent_id: null, locked: false,
      geometry: [210,350,250,360,300,364,350,360,390,350]},
  ]};
}

export function diffDesigns(before: Design, after: Design): Patch[] {
  const old = new Map(before.components.map(c => [c.id, c]));
  const current = new Map(after.components.map(c => [c.id, c]));
  const operations: Patch[] = [];
  if (before.material_id !== after.material_id) operations.push({op: 'update',
    target_component_id: 'garment', payload: {material_id: after.material_id}});
  const additions: Patch[] = [];
  const edits: Patch[] = [];
  for (const component of after.components) {
    const previous = old.get(component.id);
    if (!previous) additions.push({op: 'create', target_component_id: component.id,
      payload: {kind: component.kind, parent_id: component.parent_id, geometry: component.geometry, locked: false, layer_order: component.layer_order}});
    else {
      const payload: Record<string, unknown> = {};
      if (JSON.stringify(previous.geometry) !== JSON.stringify(component.geometry)) payload.geometry = component.geometry;
      if (previous.parent_id !== component.parent_id) payload.parent_id = component.parent_id;
      if (previous.kind !== component.kind) payload.kind = component.kind;
      if (previous.layer_order !== component.layer_order) payload.layer_order = component.layer_order;
      if (Object.keys(payload).length) edits.push({op: 'update', target_component_id: component.id, payload});
    }
  }
  const known = new Set(before.components.map(c => c.id));
  while (additions.length) {
    const index = additions.findIndex(p => !p.payload.parent_id || known.has(String(p.payload.parent_id)));
    if (index === -1) throw new Error('Invalid component hierarchy');
    const [patch] = additions.splice(index,1);
    operations.push(patch); known.add(patch.target_component_id);
  }
  operations.push(...edits);
  const removed = before.components.filter(c => !current.has(c.id));
  // Descendants first, after retained children are reparented out of deleted groups.
  while (removed.length) {
    const index = removed.findIndex(c => !removed.some(child => child.parent_id === c.id));
    if (index === -1) throw new Error('Invalid component hierarchy');
    const [component] = removed.splice(index,1);
    operations.push({op:'delete',target_component_id:component.id,payload:{}});
  }
  return operations;
}
