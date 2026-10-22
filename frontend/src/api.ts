const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

export type ApiStatus = 'ready' | 'pending' | 'empty';

export interface Health {
  status: string;
  analysis_status: ApiStatus;
  model_available: boolean;
  generated_at_utc: string | null;
  source: string;
  model_version: string | null;
}

export interface Summary {
  status: ApiStatus;
  message?: string;
  source?: string;
  updated_at?: string | null;
  model_version?: string | null;
  users_analyzed?: number;
  cancellations?: number;
  not_cancelled?: number;
  cancellation_rate?: number;
  findings?: Array<{ label: string; group: string; rate: number; users: number; cancellations: number }>;
}

export interface RateGroup {
  group: string;
  users: number;
  cancellations: number;
  rate: number;
}

export interface BehaviorGroup {
  state: string;
  users: number;
  median: number | null;
  q1: number | null;
  q3: number | null;
}

export interface SegmentResult {
  status: ApiStatus;
  message?: string;
  users: number;
  cancellations: number;
  not_cancelled: number;
  cancellation_rate: number | null;
  groups: {
    plan?: RateGroup[];
    country?: RateGroup[];
    payment_method?: RateGroup[];
    device?: RateGroup[];
  };
  behavior?: Array<{ variable: string; label: string; unit: string; groups: BehaviorGroup[] }>;
}

export interface Quality {
  status: ApiStatus;
  message?: string;
  original_rows?: number;
  final_rows?: number;
  exact_duplicates?: number;
  repeated_user_rows?: number;
  remaining_duplicate_rows?: number;
  unique_users?: number | null;
  nulls_by_variable?: Array<{ variable: string; count: number; percent: number }>;
  audit_decisions?: Array<Record<string, string | number>>;
  issue_incidences?: number;
  records_removed_or_merged?: number;
  counts_note?: string;
}

export interface ScoreMetric {
  modelo: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  train_cv_f1_mean: number;
  train_cv_f1_std: number;
}

export interface FeatureSchema {
  name: string;
  kind: 'number' | 'category';
  minimum?: number | null;
  maximum?: number | null;
  options?: string[];
  required: boolean;
}

export interface Models {
  status: ApiStatus;
  message?: string;
  updated_at?: string | null;
  model_version?: string | null;
  model_available?: boolean;
  input_schema?: FeatureSchema[];
  threshold?: number;
  positive_class?: number;
  split?: { train_fraction: number; test_fraction: number; random_state: number; stratified: boolean };
  test_rows?: number;
  test_class_counts?: Record<string, number>;
  metrics?: ScoreMetric[];
  reports?: Record<string, {
    classification_report: Record<string, Record<string, number>>;
    confusion_matrix: number[][];
    confusion_matrix_labels: string[];
  }>;
  temporal_limitation?: string;
}

export interface Factors {
  status: ApiStatus;
  message?: string;
  selected_model?: string;
  method?: { dataset: string; scoring: string; interpretation: string };
  causality_note?: string;
  items?: Array<{ variable: string; importancia_media: number }>;
}

export interface DownloadItem {
  id: string;
  filename: string;
  available: boolean;
}

export interface Prediction {
  predicted_class: number;
  label: string;
  probability_estimate: number | null;
  class_scores: Record<string, number>;
  threshold: number;
  model_version: string;
  calibration_note: string;
  academic_note: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === 'string' ? detail : detail?.message ?? `Error HTTP ${response.status}`;
    throw new Error(message);
  }
  return body as T;
}

export const api = {
  health: () => request<Health>('/health'),
  summary: () => request<Summary>('/summary'),
  quality: () => request<Quality>('/quality'),
  filters: () => request<{ status: ApiStatus; countries: string[]; plans: string[]; devices: string[] }>('/filters'),
  segments: (filters: { country: string; plan: string; device: string }) => {
    const params = new URLSearchParams();
    if (filters.country) params.set('country', filters.country);
    if (filters.plan) params.set('plan', filters.plan);
    if (filters.device) params.set('device', filters.device);
    const query = params.toString();
    return request<SegmentResult>(`/segments${query ? `?${query}` : ''}`);
  },
  models: () => request<Models>('/models'),
  factors: () => request<Factors>('/factors'),
  downloads: () => request<{ status: ApiStatus; items: DownloadItem[] }>('/downloads'),
  predict: (features: Record<string, string | number | null>) =>
    request<Prediction>('/predict', { method: 'POST', body: JSON.stringify({ features }) }),
};

export function downloadUrl(id: string): string {
  return `${API_BASE}/downloads/${encodeURIComponent(id)}`;
}
