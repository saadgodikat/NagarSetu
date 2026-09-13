'use client'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { apiFetch, resolveImageUrl } from '@/lib/api'
import { Complaint, Worker } from '@/lib/types'
import { AppShell } from '@/components/layout/AppShell'
import { StatusBadge, SeverityBadge } from '@/components/complaints/StatusBadge'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { ChevronLeft } from 'lucide-react'
import '@/lib/i18n/index'

const ALL_STEPS = [
  'submitted', 'under_review', 'assigned', 'in_progress',
  'resolution_submitted', 'verified', 'closed',
]

export default function ComplaintDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const { token, user } = useAuth()
  const [complaint, setComplaint] = useState<Complaint | null>(null)
  const [workers, setWorkers] = useState<Worker[]>([])
  const [selectedWorker, setSelectedWorker] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState('')

  async function load() {
    if (!token || !id) return
    const [c, ws] = await Promise.all([
      apiFetch<Complaint>(`/api/v1/operations/complaints/${id}`, token),
      apiFetch<Worker[]>('/api/v1/operations/workers', token),
    ])
    setComplaint(c)
    setWorkers(ws)
  }

  useEffect(() => {
    load().finally(() => setLoading(false))
  }, [token, id])

  async function doStatus(status: string) {
    if (!token || !complaint) return
    setActionLoading(true)
    setActionMsg('')
    try {
      const updated = await apiFetch<Complaint>(
        `/api/v1/operations/complaints/${complaint.id}/status`,
        token,
        { method: 'PATCH', body: JSON.stringify({ status }) }
      )
      setComplaint(updated)
      setActionMsg(`Status updated to: ${status}`)
    } catch (e: any) {
      setActionMsg(e?.message || t('error.generic'))
    } finally {
      setActionLoading(false)
    }
  }

  async function doAssign() {
    if (!token || !complaint || !selectedWorker) return
    setActionLoading(true)
    setActionMsg('')
    try {
      const updated = await apiFetch<Complaint>(
        `/api/v1/operations/complaints/${complaint.id}/assign`,
        token,
        { method: 'POST', body: JSON.stringify({ field_worker_id: selectedWorker }) }
      )
      setComplaint(updated)
      setSelectedWorker('')
      setActionMsg('Worker assigned successfully.')
    } catch (e: any) {
      setActionMsg(e?.message || t('error.generic'))
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <AppShell><p className="text-gray-400">{t('loading')}</p></AppShell>
  if (!complaint) return <AppShell><p className="text-red-500">{t('error.load')}</p></AppShell>

  const photos = complaint.images ?? []
  const beforePhoto = photos.find((p) => p.image_type === 'before')
  const afterPhoto = photos.find((p) => p.image_type === 'after')
  const progressPhotos = photos.filter((p) => p.image_type === 'progress')
  const currentStep = ALL_STEPS.indexOf(complaint.status)
  const canAct = user?.role !== 'citizen' && user?.role !== 'field_worker'

  return (
    <AppShell>
      <div className="max-w-3xl space-y-5">
        {/* Back link */}
        <Link href="/complaints" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 gap-1">
          <ChevronLeft size={16} /> {t('nav.complaints')}
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{complaint.title}</h1>
            <p className="text-xs text-gray-400 mt-1">
              #{complaint.id.slice(0, 8)} · {new Date(complaint.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <SeverityBadge severity={complaint.severity} />
            <StatusBadge status={complaint.status} />
          </div>
        </div>

        {/* Description */}
        {complaint.description && (
          <Card>
            <CardBody>
              <p className="text-sm text-gray-700">{complaint.description}</p>
            </CardBody>
          </Card>
        )}

        {/* Status Timeline */}
        <Card>
          <CardHeader title="Status Timeline" />
          <CardBody>
            <div className="flex items-center gap-0">
              {ALL_STEPS.map((step, i) => (
                <div key={step} className="flex items-center flex-1 last:flex-none">
                  <div className="flex flex-col items-center">
                    <div className={`w-3 h-3 rounded-full border-2 ${
                      i < currentStep ? 'bg-blue-600 border-blue-600'
                      : i === currentStep ? 'bg-blue-600 border-blue-600 ring-4 ring-blue-100'
                      : 'bg-white border-gray-300'
                    }`} />
                    <p className={`text-xs mt-1 text-center max-w-14 ${
                      i === currentStep ? 'text-blue-700 font-semibold' : 'text-gray-400'
                    }`}>
                      {t(`status.${step}`)}
                    </p>
                  </div>
                  {i < ALL_STEPS.length - 1 && (
                    <div className={`h-0.5 flex-1 -mt-4 ${i < currentStep ? 'bg-blue-600' : 'bg-gray-200'}`} />
                  )}
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        {/* Photos */}
        {photos.length > 0 && (
          <Card>
            <CardHeader title="Photos" />
            <CardBody>
              <div className="flex gap-3 flex-wrap">
                {beforePhoto && (
                  <div>
                    <p className="text-xs text-gray-400 mb-1">{t('complaint.photos.before')}</p>
                    <img src={resolveImageUrl(beforePhoto.url)} className="w-36 h-28 object-cover rounded-lg" alt="before" />
                  </div>
                )}
                {progressPhotos.map((p, i) => (
                  <div key={i}>
                    <p className="text-xs text-gray-400 mb-1">{t('complaint.photos.progress')}</p>
                    <img src={resolveImageUrl(p.url)} className="w-36 h-28 object-cover rounded-lg" alt="progress" />
                  </div>
                ))}
                {afterPhoto && (
                  <div>
                    <p className="text-xs text-gray-400 mb-1">{t('complaint.photos.after')}</p>
                    <img src={resolveImageUrl(afterPhoto.url)} className="w-36 h-28 object-cover rounded-lg" alt="after" />
                  </div>
                )}
              </div>
            </CardBody>
          </Card>
        )}

        {/* Details */}
        <Card>
          <CardHeader title="Details" />
          <CardBody>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.category')}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{complaint.category}</dd>
              </div>
              <div>
                <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.ward')}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{complaint.ward_name ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.department')}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{complaint.department_name ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.assignedTo')}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {complaint.assigned_to_name ?? t('complaint.notAssigned')}
                </dd>
              </div>
              {complaint.priority_score != null && (
                <div>
                  <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.priority')}</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{complaint.priority_score}</dd>
                </div>
              )}
              {complaint.sla_deadline && (
                <div>
                  <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.slaDeadline')}</dt>
                  <dd className={`font-medium mt-0.5 ${new Date(complaint.sla_deadline) < new Date() ? 'text-red-600' : 'text-orange-600'}`}>
                    {new Date(complaint.sla_deadline).toLocaleString()}
                  </dd>
                </div>
              )}
              {complaint.category_confidence != null && (
                <div>
                  <dt className="text-gray-400 text-xs uppercase tracking-wide">AI Confidence</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{Math.round(complaint.category_confidence * 100)}%</dd>
                </div>
              )}
              {complaint.verification_status && (
                <div>
                  <dt className="text-gray-400 text-xs uppercase tracking-wide">{t('complaint.verification')}</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{complaint.verification_status}</dd>
                </div>
              )}
            </dl>
          </CardBody>
        </Card>

        {/* Timeline events */}
        {complaint.timeline && complaint.timeline.length > 0 && (
          <Card>
            <CardHeader title="Audit Timeline" />
            <CardBody>
              <ol className="space-y-3">
                {[...complaint.timeline].reverse().map((e, i) => (
                  <li key={i} className="flex gap-3 text-sm border-b border-gray-50 pb-3 last:border-0 last:pb-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                    <div>
                      <p className="font-medium text-gray-800">{e.action}</p>
                      {e.new_status && (
                        <p className="text-xs text-gray-500">→ {t(`status.${e.new_status}`)}</p>
                      )}
                      <p className="text-xs text-gray-400 mt-0.5">{new Date(e.timestamp).toLocaleString()}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </CardBody>
          </Card>
        )}

        {/* Officer Actions */}
        {canAct && (
          <Card>
            <CardHeader title="Actions" />
            <CardBody className="space-y-4">
              {actionMsg && (
                <p className="text-sm text-blue-800 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 font-medium">
                  {actionMsg}
                </p>
              )}
              <div className="flex gap-2 flex-wrap">
                {(complaint.status === 'submitted' || complaint.status === 'reopened') && (
                  <>
                    <Button variant="primary" loading={actionLoading} onClick={() => doStatus('under_review')}>
                      Move to Review
                    </Button>
                    <Button variant="danger" loading={actionLoading} onClick={() => doStatus('rejected')}>
                      {t('action.reject')}
                    </Button>
                  </>
                )}
                {complaint.status === 'under_review' && (
                  <Button variant="danger" loading={actionLoading} onClick={() => doStatus('rejected')}>
                    {t('action.reject')}
                  </Button>
                )}
                {complaint.status === 'resolution_submitted' && (
                  <>
                    <Button loading={actionLoading} onClick={() => doStatus('verified')}>
                      {t('action.verify')}
                    </Button>
                    <Button variant="secondary" loading={actionLoading} onClick={() => doStatus('reopened')}>
                      Request Rework
                    </Button>
                  </>
                )}
                {complaint.status === 'verified' && (
                  <Button variant="secondary" loading={actionLoading} onClick={() => doStatus('reopened')}>
                    {t('action.reopen')}
                  </Button>
                )}
              </div>

              {/* Assign worker */}
              {complaint.status !== 'closed' && complaint.status !== 'rejected' && (
                <div className="flex gap-2 items-end pt-2 border-t border-gray-100">
                  <Select
                    label={t('worker.assignTo')}
                    value={selectedWorker}
                    onChange={(e) => setSelectedWorker(e.target.value)}
                    className="flex-1"
                  >
                    <option value="">{t('worker.selectWorker')}</option>
                    {workers
                      .filter(
                        (w) =>
                          !complaint.assigned_department_id ||
                          !w.department_id ||
                          w.department_id === complaint.assigned_department_id
                      )
                      .map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name}
                        </option>
                      ))}
                  </Select>
                  <Button onClick={doAssign} disabled={!selectedWorker} loading={actionLoading}>
                    {t('action.assign')}
                  </Button>
                </div>
              )}
            </CardBody>
          </Card>
        )}
      </div>
    </AppShell>
  )
}
