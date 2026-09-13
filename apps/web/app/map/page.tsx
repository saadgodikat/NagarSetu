'use client'
import dynamic from 'next/dynamic'
import { useTranslation } from 'react-i18next'
import { AppShell } from '@/components/layout/AppShell'
import '@/lib/i18n/index'

const ComplaintMap = dynamic(
  () => import('@/components/map/ComplaintMap').then((m) => m.ComplaintMap),
  {
    ssr: false,
    loading: () => <p className="text-gray-400 p-4">Loading map...</p>,
  }
)

export default function MapPage() {
  const { t } = useTranslation()
  return (
    <AppShell>
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900">{t('map.title')}</h1>
        <ComplaintMap />
      </div>
    </AppShell>
  )
}
