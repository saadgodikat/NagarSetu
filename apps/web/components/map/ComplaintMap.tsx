'use client'
import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useAuth } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { Complaint } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { Select } from '@/components/ui/Select'

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  MEDIUM: '#ca8a04',
  LOW: '#16a34a',
}

export function ComplaintMap() {
  const { token } = useAuth()
  const { t } = useTranslation()
  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    if (!token) return
    const params = new URLSearchParams()
    if (severityFilter) params.set('severity', severityFilter)
    if (statusFilter) params.set('status', statusFilter)
    apiFetch<{ data: Complaint[] }>(`/api/v1/operations/complaints?limit=500&${params}`, token)
      .then((r) => setComplaints(r.data))
      .catch(console.error)
  }, [token, severityFilter, statusFilter])

  const withGeo = complaints.filter((c) => c.location_lat && c.location_lng)

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="w-40">
          <option value="">{t('complaint.severity')}</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
            <option key={s} value={s}>{t(`severity.${s}`)}</option>
          ))}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-44">
          <option value="">{t('complaint.status')}</option>
          {['submitted', 'under_review', 'assigned', 'in_progress', 'resolution_submitted', 'verified', 'closed'].map((s) => (
            <option key={s} value={s}>{t(`status.${s}`)}</option>
          ))}
        </Select>
        <p className="text-sm text-gray-500 self-center">{withGeo.length} complaints</p>
      </div>

      <div className="rounded-xl overflow-hidden border border-gray-200" style={{ height: '65vh' }}>
        <MapContainer center={[17.686, 75.901]} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />
          {withGeo.map((c) => (
            <CircleMarker
              key={c.id}
              center={[c.location_lat!, c.location_lng!]}
              radius={8}
              pathOptions={{
                color: SEVERITY_COLORS[c.severity] ?? '#6b7280',
                fillColor: SEVERITY_COLORS[c.severity] ?? '#6b7280',
                fillOpacity: 0.8,
                weight: 1,
              }}
            >
              <Popup>
                <div className="text-sm space-y-1">
                  <p className="font-semibold">{c.title}</p>
                  <p className="text-gray-500">
                    {t(`status.${c.status}`)} · {t(`severity.${c.severity}`)}
                  </p>
                  {c.ward_name && <p className="text-gray-400 text-xs">{c.ward_name}</p>}
                  <Link
                    href={`/complaints/${c.id}`}
                    className="text-blue-600 hover:underline text-xs"
                  >
                    {t('action.viewDetails')} →
                  </Link>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
