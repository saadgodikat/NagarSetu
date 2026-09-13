'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'

export default function Root() {
  const { token, user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!token) {
      router.replace('/login')
    } else if (user?.role === 'admin' || user?.role === 'department_head') {
      router.replace('/dashboard')
    } else {
      router.replace('/complaints')
    }
  }, [token, user, router])

  return null
}
