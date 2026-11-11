'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { BaseBoxShapeUtil, b64Vecs, createShapeId, Editor, Polyline2d, Rectangle2d,
  SVGContainer, T, Tldraw, Vec, useEditor, useValue,
  type TLBaseShape, type TLShape, type TLUiOverrides } from 'tldraw';
import { getAssetUrls } from '@tldraw/assets/selfHosted';
import type { Component, Design } from '@/lib/types';
import 'tldraw/tldraw.css';

type GarmentProps = {componentId: string; kind: string; points: number[]; w: number; h: number};
type GarmentShape = TLBaseShape<'garment-component', GarmentProps>;
declare module '@tldraw/tlschema' { interface TLGlobalShapePropsMap { 'garment-component': GarmentProps } }

function points(shape: GarmentShape): Vec[] {
  const result: Vec[] = [];
  for (let i = 0; i < shape.props.points.length; i += 2) {
    result.push(new Vec(shape.props.points[i] * shape.props.w, shape.props.points[i+1] * shape.props.h));
  }
  return result;
}
function path(shape: GarmentShape): string {
  return points(shape).map((point,index) => `${index ? 'L' : 'M'}${point.x},${point.y}`).join(' ');
}

class GarmentShapeUtil extends BaseBoxShapeUtil<GarmentShape> {
  static override type = 'garment-component' as const;
  static override props = {componentId: T.string, kind: T.string, points: T.arrayOf(T.number), w: T.number, h: T.number};
  override getDefaultProps(): GarmentProps { return {componentId: '', kind: 'freehand', points: [], w: 1, h: 1}; }
  override canEdit() { return false; }
  override getGeometry(shape: GarmentShape) {
    const vertices = points(shape);
    return vertices.length > 1 ? new Polyline2d({points: vertices}) : new Rectangle2d({width: shape.props.w, height: shape.props.h, isFilled: false});
  }
  override component(shape: GarmentShape) {
    return <SVGContainer><path d={path(shape)} fill="none" stroke={shape.isLocked ? '#92713f' : '#334d48'}
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      {shape.props.points.length === 0 && <circle cx="0" cy="0" r="3" fill="#334d48"/>}</SVGContainer>;
  }
  override getIndicatorPath(shape: GarmentShape) { return new Path2D(path(shape)); }
}

function ancestorOrigin(component: Component, all: Map<string, Component>): {x: number; y: number} {
  const parent = component.parent_id ? all.get(component.parent_id) : undefined;
  if (!parent || parent.kind === 'group' || parent.geometry.length < 2) return {x: 0, y: 0};
  return {x: Math.min(...parent.geometry.filter((_,i) => i % 2 === 0)),
    y: Math.min(...parent.geometry.filter((_,i) => i % 2 === 1))};
}

function renderDesign(editor: Editor, design: Design) {
  editor.run(() => {
    const shapes = editor.getCurrentPageShapes();
    if (shapes.length) editor.deleteShapes(shapes.map(s => s.id));
    const all = new Map(design.components.map(c => [c.id, c]));
    const remaining = [...design.components].sort((a,b) => (a.layer_order || '').localeCompare(b.layer_order || ''));
    const created = new Set<string>();
    while (remaining.length) {
      const index = remaining.findIndex(c => !c.parent_id || created.has(c.parent_id));
      if (index === -1) throw new Error('Invalid component hierarchy');
      const [component] = remaining.splice(index, 1);
      const parentId = component.parent_id ? createShapeId(component.parent_id) : editor.getCurrentPageId();
      if (component.kind === 'group') {
        editor.createShape({id: createShapeId(component.id), type: 'group', parentId,
          index: component.layer_order as TLShape['index'], x: 0, y: 0, isLocked: component.locked});
      } else {
        const xs = component.geometry.filter((_,i) => i % 2 === 0);
        const ys = component.geometry.filter((_,i) => i % 2 === 1);
        const x = xs.length ? Math.min(...xs) : 0, y = ys.length ? Math.min(...ys) : 0;
        const w = Math.max(1, (xs.length ? Math.max(...xs) : x) - x);
        const h = Math.max(1, (ys.length ? Math.max(...ys) : y) - y);
        const normalized = component.geometry.map((value,i) => (value - (i % 2 ? y : x)) / (i % 2 ? h : w));
        const parentOrigin = ancestorOrigin(component, all);
        editor.createShape<GarmentShape>({id: createShapeId(component.id), type: 'garment-component',
          parentId, index: component.layer_order as TLShape['index'], x: x-parentOrigin.x, y: y-parentOrigin.y,
          isLocked: component.locked, props: {componentId: component.id, kind: component.kind, points: normalized, w, h}});
      }
      created.add(component.id);
    }
  }, {history: 'ignore', ignoreShapeLock: true});
}

function extractDesign(editor: Editor, original: Design): Design {
  const originalComponents = new Map(original.components.map(c => [c.id,c]));
  const shapes = editor.getCurrentPageShapesSorted();
  const components: Component[] = [];
  for (const shape of shapes) {
    if (!['garment-component', 'draw', 'group'].includes(shape.type)) {
      throw new Error('Only garment components, freehand strokes and groups can be saved. Remove unsupported objects.');
    }
    const id = shape.id.slice(6);
    const parentId = shape.parentId.startsWith('shape:') ? shape.parentId.slice(6) : null;
    let vertices: {x: number; y: number}[] = [];
    if (shape.type === 'garment-component') vertices = points(shape);
    else if (shape.type === 'draw') vertices = shape.props.segments.flatMap(s =>
      b64Vecs.decodePoints(s.path, s.dim).map(p => ({x: p.x * shape.props.scaleX, y: p.y * shape.props.scaleY})));
    const matrix = editor.getShapePageTransform(shape);
    const geometry = vertices.flatMap(p => { const v = matrix.applyToPoint(p); return [Math.round(v.x), Math.round(v.y)]; });
    components.push({id, kind: shape.type === 'garment-component' ? shape.props.kind : shape.type === 'draw' ? 'freehand' : 'group',
      geometry, parent_id: parentId, locked: originalComponents.get(id)?.locked || false, layer_order: shape.index});
  }
  return {components, material_id: original.material_id};
}

const overrides: TLUiOverrides = {tools: (_editor, tools) => Object.fromEntries(
  ['select','draw','eraser','hand'].map(id => [id, tools[id]]))};

function DrawingTools() {
  const editor = useEditor();
  const tool = useValue('current tool', () => editor.getCurrentToolId(), [editor]);
  const readonly = useValue('read only', () => editor.getInstanceState().isReadonly, [editor]);
  const canUndo = useValue('undo', () => editor.getCanUndo(), [editor]);
  const canRedo = useValue('redo', () => editor.getCanRedo(), [editor]);
  return <div className="drawing-tools" aria-label="Drawing tools">
    {(['select','draw','eraser','hand'] as const).map(id => <button key={id} aria-pressed={tool === id}
      disabled={readonly} onClick={() => editor.setCurrentTool(id)}>{id === 'draw' ? 'Draw' : id[0].toUpperCase()+id.slice(1)}</button>)}
    <span className="tool-divider"/>
    <button disabled={readonly || !canUndo} onClick={() => editor.undo()} aria-label="Undo drawing edit">↶ Undo</button>
    <button disabled={readonly || !canRedo} onClick={() => editor.redo()} aria-label="Redo drawing edit">↷ Redo</button>
  </div>;
}

const shapeUtils = [GarmentShapeUtil];
const assetUrls = getAssetUrls({baseUrl: '/tldraw-assets'});
const components = {Toolbar: DrawingTools, MainMenu: null, PageMenu: null, StylePanel: null,
  ActionsMenu: null, QuickActions: null, SharePanel: null, ContextMenu: null};

export function GarmentCanvas({design, readonly, onChange, onSelect, selected}: {
  design: Design; readonly: boolean; onChange: (design: Design) => void;
  onSelect: (id: string | null) => void; selected: string | null;
}) {
  const editor = useRef<Editor | null>(null);
  const latest = useRef({design, readonly, onChange, onSelect});
  const syncing = useRef(false);
  const exported = useRef('');
  const [problem, setProblem] = useState('');
  useEffect(() => {latest.current = {design, readonly, onChange, onSelect};});
  useEffect(() => {
    if (!editor.current || JSON.stringify(design) === exported.current) return;
    syncing.current = true;
    renderDesign(editor.current, design);
    exported.current = JSON.stringify(design);
    syncing.current = false;
  }, [design]);
  useEffect(() => {editor.current?.updateInstanceState({isReadonly: readonly});}, [readonly]);
  useEffect(() => {
    if (!editor.current || !selected) return;
    const id = createShapeId(selected);
    if (editor.current.getShape(id)) editor.current.select(id);
  }, [selected]);
  const mount = useCallback((instance: Editor) => {
    editor.current = instance;
    renderDesign(instance, latest.current.design);
    exported.current = JSON.stringify(latest.current.design);
    instance.zoomToFit({animation: {duration: 0}});
    instance.updateInstanceState({isReadonly: latest.current.readonly});
    const protectedNodes = new Set<string>();
    const nodes = new Map(latest.current.design.components.map(c => [c.id, c]));
    for (const component of nodes.values()) if (component.locked) {
      let current: Component | undefined = component;
      while (current) {protectedNodes.add(current.id); current = current.parent_id ? nodes.get(current.parent_id) : undefined;}
    }
    const guardChange = instance.sideEffects.registerBeforeChangeHandler('shape', (previous, next) => {
      if (syncing.current) return next;
      if (protectedNodes.has(previous.id.slice(6))) return previous;
      return next.isLocked !== previous.isLocked ? {...next, isLocked: previous.isLocked} : next;
    });
    const guardDelete = instance.sideEffects.registerBeforeDeleteHandler('shape', shape => {
      if (!syncing.current && protectedNodes.has(shape.id.slice(6))) return false;
    });
    const documents = instance.store.listen(() => {
      if (syncing.current) return;
      try {
        const next = extractDesign(instance, latest.current.design);
        exported.current = JSON.stringify(next);
        latest.current.onChange(next);
        setProblem('');
      } catch (error) {setProblem(error instanceof Error ? error.message : 'This drawing cannot be saved.');}
    }, {scope: 'document', source: 'user'});
    const selection = instance.store.listen(() => {
      latest.current.onSelect(instance.getSelectedShapeIds()[0]?.slice(6) || null);
    }, {scope: 'session', source: 'user'});
    return () => {documents(); selection(); guardChange(); guardDelete(); editor.current = null;};
  }, []);
  if (process.env.NODE_ENV === 'production' && !process.env.NEXT_PUBLIC_TLDRAW_LICENSE_KEY) {
    return <div className="canvas-loading" role="status">The production drawing editor needs a configured tldraw license. Your saved design remains available.</div>;
  }
  return <><Tldraw shapeUtils={shapeUtils} components={components} overrides={overrides} assetUrls={assetUrls}
    onMount={mount} licenseKey={process.env.NEXT_PUBLIC_TLDRAW_LICENSE_KEY}>
  </Tldraw>{problem && <div className="canvas-problem" role="alert">{problem}</div>}</>;
}
