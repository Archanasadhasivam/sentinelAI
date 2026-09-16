export type Decision = "allow" | "wait" | "block";
export type EventType = "prompt" | "tool_call" | "api_request" | "output";

export interface Evidence {
  detector: string;
  label: string;
  detail: string;
  weight: number;
}

export interface DetectionResult {
  detector_name: string;
  score: number;
  triggered: boolean;
  evidence: Evidence[];
  metadata: Record<string, unknown>;
}

export interface Verdict {
  id?: string;
  decision: Decision;
  risk_score: number;
  likelihood: number;
  impact: number;
  dominant_factor: string;
  narrative: string | null;
}

export interface SentinelEvent {
  id: string;
  session_id?: string;
  event_type: EventType;
  source: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
  detections: DetectionResult[];
  verdict: Verdict | null;
}

export interface Alert {
  id: string;
  event_id: string;
  tier: "info" | "warning" | "critical";
  message: string;
  acknowledged: boolean;
  created_at: string;
}

export interface TrustReport {
  verdict_id: string;
  event_id: string;
  decision: Decision;
  risk_score: number;
  likelihood: number;
  impact: number;
  alpha: number;
  dominant_factor: string;
  structured_report: {
    detector_breakdown: DetectionResult[];
    [key: string]: unknown;
  };
  narrative: string | null;
  created_at: string;
}

export interface FixturePayload {
  id: string;
  category: string;
  label: string;
  text: string;
  expected: Decision;
}

export interface WSMessage {
  kind: "event_created" | "detection_result" | "verdict" | "alert";
  data: Record<string, any>;
}

export interface PolicyConfig {
  thresholds: { block: number; wait: number };
  risk: { alpha: number; impact_floor: number };
  detector_weights: Record<string, number>;
  action_impact: Record<string, number>;
}
