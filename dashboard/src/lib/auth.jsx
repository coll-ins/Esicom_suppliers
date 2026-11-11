import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { get, post, setLoggedOutHandler } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [me, setMe] = useState(undefined) // undefined = checking, null = logged out

  const refresh = useCallback(() => get('/auth/me/').then(setMe).catch(() => setMe(null)), [])

  useEffect(() => {
    setLoggedOutHandler(() => setMe(null))
    refresh()
  }, [refresh])

  const login = async (email, password) => {
    await post('/auth/login/', { email, password })
    await refresh()
  }
  const logout = async () => {
    await post('/auth/logout/').catch(() => {})
    setMe(null)
  }
  const logoutEverywhere = async () => {
    await post('/auth/logout-all/')
    setMe(null)
  }

  return <AuthContext.Provider value={{ me, login, logout, logoutEverywhere, refresh }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

export function useIsOwner() {
  return useAuth().me?.role === 'owner'
}
