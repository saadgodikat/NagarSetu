import clsx from 'clsx'

export type BadgeColor = 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray' | 'purple'

interface Props {
  label: string
  color?: BadgeColor
  className?: string
}

const colors: Record<BadgeColor, string> = {
  red: 'bg-red-100 text-red-700',
  orange: 'bg-orange-100 text-orange-700',
  yellow: 'bg-yellow-100 text-yellow-800',
  green: 'bg-green-100 text-green-700',
  blue: 'bg-blue-100 text-blue-700',
  gray: 'bg-gray-100 text-gray-600',
  purple: 'bg-purple-100 text-purple-700',
}

export function Badge({ label, color = 'gray', className }: Props) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', colors[color], className)}>
      {label}
    </span>
  )
}
