'use client'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { Complaint } from '@/lib/types'
import { AppShell } from '@/components/layout/AppShell'
import { StatusBadge, SeverityBadge } from '@/components/complaints/StatusBadge'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import '@/lib/i18n/index'

const STATUSES = ['submitted', 'under_review', 'assigned', 'in_progress', 'resolution_submitted', 'verified', 'closed']
const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export default function ComplaintsPage() {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')

  useEffect(() => {
    if (!token) return
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    if (severityFilter) params.set('severity', severityFilter)
    setLoading(true)
    apiFetch<{ data: Complaint[] }>(`/api/v1/operations/complaints?${params}`, token)
      .then((r) => setComplaints(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token, statusFilter, severityFilter])

  return (
    <AppShell>
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900">{t('nav.complaints')}</h1>

        {/* Filters */}
        <div className="flex gap-3 flex-wrap">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-44">
            <option value="">{t('complaint.status')}</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{t(`status.${s}`)}</option>
            ))}
          </Select>
          <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="w-44">
            <option value="">{t('complaint.severity')}</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>{t(`severity.${s}`)}</option>
            ))}
          </Select>
        </div>

        {loading ? (
          <p className="text-gray-400">{t('loading')}</p>
        ) : (
          <Card>
            <div className="divide-y divide-gray-100">
              {complaints.length === 0 && (
                <p className="p-8 text-gray-400 text-sm text-center">{t('complaint.noComplaints')}</p>
              )}
              {complaints.map((c) => (
                <Link
                  key={c.id}
                  href={`/complaints/${c.id}`}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-700">
                      {c.title}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      #{c.id.slice(0, 8)} · {c.ward_name ?? ''} · {new Date(c.created_at).toLocaleDateString()}
                      {c.assigned_to_name && ` · ${c.assigned_to_name}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {c.sla_deadline && new Date(c.sla_deadline) < new Date() && (
                      <span className="text-xs text-red-500 font-medium">⚠ Overdue</span>
                    )}
                    <SeverityBadge severity={c.severity} />
                    <StatusBadge status={c.status} />
                  </div>
                </Link>
              ))}
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  )
}
