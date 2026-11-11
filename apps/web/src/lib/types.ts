export interface Component {
  id: string;
  kind: string;
  parent_id: string | null;
  geometry: number[];
  locked: boolean;
  layer_order?: string | null;
}
export interface Design { components: Component[]; material_id: string | null }
export interface Approval {
  id: string; revision_id: string; purpose: 'aesthetic' | 'technical' | 'handoff';
  decision: 'approve' | 'reject'; role: string; actor_id: string;
}
export interface Garment {
  id: string; project_id: string; name: string; draft_revision_id: string;
  approved_revision_id: string | null; content_hash: string; design: Design;
  approvals: Approval[];
}
export interface Patch {
  op: 'create' | 'update' | 'delete'; target_component_id: string;
  payload: Record<string, unknown>;
}
export interface RevisionResult {
  new_revision: string; content_hash: string; diff: string[];
  invalidated_artifacts: string[]; approval_status: 'unapproved';
}
export interface Project { id: string; name: string }
export interface GarmentSummary {
  id: string; name: string; draft_revision_id: string; approved_revision_id: string | null;
}
export interface AuditEvent {
  id: string; event_type: string; revision_id: string | null; created_at: string;
  detail: Record<string, unknown>;
}
export interface SampleMeasurement {label: string; value: string; unit: 'mm' | 'cm' | 'in'; source: string}
export interface SampleFinding {
  id: string; sample_label: string; component_id: string | null; observation: string;
  severity: 'note' | 'blocking'; measurement: SampleMeasurement | null;
  thumbnail_jpeg: string | null; annotation: {x: number; y: number} | null;
  recorded_by: string; recorded_at: string;
  resolution: {id: string; note: string; by: string; at: string} | null;
}
