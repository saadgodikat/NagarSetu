'use client'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from './types'

interface AuthCtx {
  token: string
  user: User | null
  login: (token: string, user: User) => void
  logout: () => void
}

const Ctx = createContext<AuthCtx>({
  token: '',
  user: null,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState('')
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    const t = localStorage.getItem('smcp_token')
    const u = localStorage.getItem('smcp_user')
    if (t && u) {
      setToken(t)
      try { setUser(JSON.parse(u)) } catch { /* invalid */ }
    }
  }, [])

  const login = (t: string, u: User) => {
    setToken(t)
    setUser(u)
    localStorage.setItem('smcp_token', t)
    localStorage.setItem('smcp_user', JSON.stringify(u))
  }

  const logout = () => {
    setToken('')
    setUser(null)
    localStorage.removeItem('smcp_token')
    localStorage.removeItem('smcp_user')
  }

  return <Ctx.Provider value={{ token, user, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
