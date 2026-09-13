'use client'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { Role } from '@/lib/types'

export function RoleGuard({ allowed, children }: { allowed: Role[]; children: React.ReactNode }) {
  const { user, token } = useAuth()
  const router = useRouter()
  useEffect(() => {
    if (!token) router.push('/login')
    else if (user && !allowed.includes(user.role)) router.push('/complaints')
  }, [token, user])
  if (!user) return null
  return <>{children}</>
}
