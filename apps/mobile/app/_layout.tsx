import { useEffect } from 'react'
import { Slot, useRouter, useSegments } from 'expo-router'
import { AuthProvider, useAuth } from '@/lib/auth'
import '@/lib/i18n/index'

function AuthGate() {
  const { token, user, loading } = useAuth()
  const router = useRouter()
  const segments = useSegments()

  useEffect(() => {
    if (loading) return
    const inAuth = segments[0] === '(auth)'
    if (!token && !inAuth) {
      router.replace('/(auth)/login')
    } else if (token && inAuth) {
      if (user?.role === 'field_worker') {
        router.replace('/(worker)/tasks')
      } else {
        router.replace('/(citizen)/home')
      }
    }
  }, [token, user, loading, segments, router])

  return <Slot />
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}
