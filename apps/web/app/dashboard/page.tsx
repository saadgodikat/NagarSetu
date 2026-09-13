'use client'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { Analytics } from '@/lib/types'
import { AppShell } from '@/components/layout/AppShell'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { AlertTriangle, Clock, Users, AlertCircle, TrendingUp, CheckCircle2 } from 'lucide-react'
import '@/lib/i18n/index'

function KPICard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color: string
}) {
  return (
    <Card className="flex items-center gap-4 px-5 py-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
      </div>
    </Card>
  )
}

export default function DashboardPage() {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    apiFetch<Analytics>('/api/v1/analytics/summary', token)
      .then(setData)
      .catch(() => setError(t('error.load')))
      .finally(() => setLoading(false))
  }, [token, t])

  const resRate = data ? `${Math.round(data.resolution_rate * 100)}%` : '—'
  const avgHrs = data?.average_resolution_hours
    ? `${Math.round(data.average_resolution_hours)}${t('dashboard.hours')}`
    : '—'

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-xl font-bold text-gray-900">{t('dashboard.title')}</h1>

        {loading && <p className="text-gray-400">{t('loading')}</p>}
        {error && <p className="text-red-500">{error}</p>}

        {data && (
          <>
            {/* Primary KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard label={t('dashboard.critical')} value={data.critical_complaints} icon={AlertTriangle} color="bg-red-500" />
              <KPICard label={t('dashboard.overdue')} value={data.overdue_complaints} icon={Clock} color="bg-orange-500" />
              <KPICard label={t('dashboard.unassigned')} value={data.unassigned_complaints} icon={Users} color="bg-yellow-500" />
              <KPICard label={t('dashboard.emerging')} value={data.emerging_issues.length} icon={AlertCircle} color="bg-purple-500" />
            </div>

            {/* Secondary KPIs */}
            <div className="grid grid-cols-3 gap-4">
              <KPICard label={t('dashboard.open')} value={data.open_complaints} icon={TrendingUp} color="bg-blue-500" />
              <KPICard label={t('dashboard.resolutionRate')} value={resRate} icon={CheckCircle2} color="bg-green-500" />
              <KPICard label={t('dashboard.avgResolution')} value={avgHrs} icon={Clock} color="bg-gray-500" />
            </div>

            {/* Emerging Alerts */}
            {data.emerging_issues.length > 0 && (
              <Card>
                <CardHeader title={t('dashboard.emergingAlerts')} />
                <CardBody>
                  <div className="space-y-2">
                    {data.emerging_issues.map((issue, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{issue.category}</p>
                          <p className="text-xs text-gray-500">
                            {issue.open_count} open · {issue.count} total
                          </p>
                        </div>
                        <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-1 rounded-full">
                          Spike
                        </span>
                      </div>
                    ))}
                  </div>
                </CardBody>
              </Card>
            )}

            {/* Department Workload */}
            <Card>
              <CardHeader title={t('dashboard.deptWorkload')} />
              <CardBody>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-gray-100">
                      <th className="pb-3 font-medium">{t('complaint.department')}</th>
                      <th className="pb-3 text-center font-medium">Total</th>
                      <th className="pb-3 text-center font-medium">{t('dashboard.open')}</th>
                      <th className="pb-3 text-center font-medium">{t('dashboard.overdue')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.department_workload.map((d, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                        <td className="py-2.5 font-medium text-gray-900">{d.department_name}</td>
                        <td className="py-2.5 text-center text-gray-600">{d.total}</td>
                        <td className="py-2.5 text-center text-gray-600">{d.open}</td>
                        <td className="py-2.5 text-center font-medium text-red-600">{d.overdue}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  )
}
