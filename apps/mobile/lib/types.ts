export type Role = 'citizen' | 'field_worker' | 'officer' | 'department_head' | 'admin'
export type ComplaintStatus =
  | 'submitted'
  | 'under_review'
  | 'assigned'
  | 'in_progress'
  | 'resolution_submitted'
  | 'verified'
  | 'closed'
  | 'reopened'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface User {
  id: string
  name: string
  email: string
  role: Role
}

export interface ComplaintSummary {
  id: string
  title: string
  description: string
  status: ComplaintStatus
  category: string
  created_at: string
  priority_score?: number | null
  verification_status?: string | null
  assigned_to_name?: string | null
  location_lat?: number
  location_lng?: number
  images?: Array<{ url: string; image_type?: string }>
  timeline?: Array<{ action: string; new_status?: string | null; timestamp: string }>
}

export interface AiClassifyResult {
  category: string
  confidence: number
  source: string
  severity: Severity
  severity_reason: string[]
  suggested_department_id: number
}

export interface Assignment {
  id: string
  complaint_id: string
  complaint_title: string
  status: string
  location_lat?: number
  location_lng?: number
  notes?: string
  priority?: number
}
