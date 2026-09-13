import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { User } from './types'

interface AuthCtx {
  token: string
  user: User | null
  login: (token: string, user: User) => Promise<void>
  logout: () => Promise<void>
  loading: boolean
}

const Ctx = createContext<AuthCtx>({
  token: '',
  user: null,
  login: async () => {},
  logout: async () => {},
  loading: true,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState('')
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      AsyncStorage.getItem('smcp_token'),
      AsyncStorage.getItem('smcp_user'),
    ])
      .then(([t, u]) => {
        if (t) setToken(t)
        if (u) {
          try {
            setUser(JSON.parse(u))
          } catch {
            /* ignore */
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const login = async (t: string, u: User) => {
    setToken(t)
    setUser(u)
    await AsyncStorage.setItem('smcp_token', t)
    await AsyncStorage.setItem('smcp_user', JSON.stringify(u))
  }

  const logout = async () => {
    setToken('')
    setUser(null)
    await AsyncStorage.removeItem('smcp_token')
    await AsyncStorage.removeItem('smcp_user')
  }

  return (
    <Ctx.Provider value={{ token, user, login, logout, loading }}>
      {children}
    </Ctx.Provider>
  )
}

export const useAuth = () => useContext(Ctx)
