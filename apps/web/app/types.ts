export type Complaint = {
  id: string;
  title: string;
  description: string;
  category: string;
  category_confidence: number | null;
  classification_source: string | null;
  severity: string;
  priority_score: number | null;
  status: string;
  sla_deadline?: string | null;
  escalated_at?: string | null;
  breach_probability?: number | null;
  escalation_level?: string | null;
  sla_predicted_at?: string | null;
  verification_status?: string | null;
  verification_score?: number | null;
  verified_at?: string | null;
  citizen_rating?: number | null;
  citizen_feedback?: string | null;
  created_at: string;
  location_lat?: number;
  location_lng?: number;
  ward_name?: string | null;
  ward_id?: number | null;
  images?: Array<{ url: string; image_type: string }>;
  assigned_to_name?: string | null;
  assigned_to?: string | null;
  related_count?: number;
  timeline?: Array<{ action: string; old_status?: string; new_status?: string; timestamp: string }>;
};

export type Worker = { id: string; name: string };

export type Analytics = {
  total_complaints: number;
  open_complaints: number;
  critical_complaints: number;
  overdue_complaints: number;
  unassigned_complaints: number;
  resolution_rate: number;
  average_resolution_hours: number | null;
  status_breakdown: Record<string, number>;
  department_workload: Array<{ department_id: number | null; department_name: string; total: number; open: number; overdue: number }>;
  ward_distribution: Array<{ ward_id: number | null; ward_name: string; zone_id: number | null; total: number }>;
  emerging_issues: Array<{ category: string; count: number; open_count: number }>;
};

export type CrisisAlert = {
  category: string;
  ward_id: number | null;
  ward_name: string;
  current_count: number;
  previous_count: number;
  pct_increase: number;
  open_count: number;
  recommendation: string;
  severity: string;
};

export type WorkerRec = {
  worker_id: string;
  worker_name: string;
  active_tasks: number;
  distance_km: number | null;
  department_match: boolean;
  score: number;
  reason: string;
};

export type AssistantAnswer = {
  question: string;
  intent: string;
  answer: string;
  data: Record<string, unknown>;
  supported_questions: string[];
};

export type ClassifyOut = {
  category: string;
  confidence: number;
  source: string;
  severity: string;
  severity_reason: string[];
  suggested_department_id: number;
};

export type VerificationReport = {
  complaint_id: string;
  verified: boolean;
  status: string;
  composite_score: number;
  signals: Record<string, unknown>;
  recommendation: string;
  flags: string[];
  evaluated_at: string;
  source: string;
};

export type NearbyComplaint = {
  id: string;
  category: string;
  status: string;
  severity: string;
  reported_date: string;
  location_lat: number;
  location_lng: number;
  ward_name: string | null;
};
