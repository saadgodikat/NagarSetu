'use client'
import { useTranslation } from 'react-i18next'
import { Badge } from '../ui/Badge'
import { BadgeColor } from '../ui/Badge'
import { ComplaintStatus, Severity } from '@/lib/types'

const statusColors: Record<ComplaintStatus, BadgeColor> = {
  submitted: 'blue',
  under_review: 'yellow',
  assigned: 'blue',
  in_progress: 'orange',
  resolution_submitted: 'yellow',
  verified: 'green',
  closed: 'green',
  reopened: 'red',
  rejected: 'red',
}

const severityColors: Record<Severity, BadgeColor> = {
  CRITICAL: 'red',
  HIGH: 'orange',
  MEDIUM: 'yellow',
  LOW: 'green',
}

export function StatusBadge({ status }: { status: ComplaintStatus }) {
  const { t } = useTranslation()
  return <Badge label={t(`status.${status}`)} color={statusColors[status]} />
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const { t } = useTranslation()
  return <Badge label={t(`severity.${severity}`)} color={severityColors[severity]} />
}
