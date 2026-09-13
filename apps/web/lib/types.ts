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
  | 'rejected'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface User {
  id: string
  name: string
  email: string
  role: Role
  department_id?: number | null
}

export interface Complaint {
  id: string
  title: string
  description: string
  category: string
  category_confidence: number | null
  classification_source: string | null
  severity: Severity
  priority_score: number | null
  status: ComplaintStatus
  sla_deadline?: string | null
  escalated_at?: string | null
  breach_probability?: number | null
  escalation_level?: string | null
  verification_status?: string | null
  verification_score?: number | null
  verified_at?: string | null
  citizen_rating?: number | null
  citizen_feedback?: string | null
  created_at: string
  images?: Array<{ url: string; image_type: string }>
  assigned_to_name?: string | null
  timeline?: Array<{ action: string; old_status?: string; new_status?: string; timestamp: string }>
  location_lat?: number | null
  location_lng?: number | null
  ward_name?: string | null
  zone_name?: string | null
  department_name?: string | null
  assigned_department_id?: number | null
}

export interface Worker {
  id: string
  name: string
  department_id?: number | null
}

export interface Analytics {
  total_complaints: number
  open_complaints: number
  critical_complaints: number
  overdue_complaints: number
  unassigned_complaints: number
  resolution_rate: number
  average_resolution_hours: number | null
  status_breakdown: Record<string, number>
  department_workload: Array<{
    department_id: number | null
    department_name: string
    total: number
    open: number
    overdue: number
  }>
  ward_distribution: Array<{
    ward_id: number | null
    ward_name: string
    zone_id: number | null
    total: number
  }>
  emerging_issues: Array<{ category: string; count: number; open_count: number }>
}

export interface Notification {
  id: string
  message: string
  read: boolean
  created_at: string
}
