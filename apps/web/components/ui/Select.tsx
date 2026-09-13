import { SelectHTMLAttributes } from 'react'
import clsx from 'clsx'

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

export function Select({ label, className, children, ...props }: Props) {
  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-medium text-gray-700">{label}</label>}
      <select
        {...props}
        className={clsx(
          'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
          className
        )}
      >
        {children}
      </select>
    </div>
  )
}
