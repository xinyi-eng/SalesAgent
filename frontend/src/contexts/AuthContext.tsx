/**
 * AuthContext - Authentication state management
 */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface User {
  id: string
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  role: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  updateUser: (updates: Partial<User>) => void
}

const AuthContext = createContext<AuthContextType | null>(null)

const AUTH_STORAGE_KEY = 'sales_agent_auth'

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true
  })

  // Load auth state from storage on mount
  useEffect(() => {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY)
    if (stored) {
      try {
        const { user, token } = JSON.parse(stored)
        // In production, validate token with backend
        if (token && user) {
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false
          })
        }
      } catch {
        localStorage.removeItem(AUTH_STORAGE_KEY)
        setAuthState({ user: null, isAuthenticated: false, isLoading: false })
      }
    } else {
      setAuthState({ user: null, isAuthenticated: false, isLoading: false })
    }
  }, [])

  const login = async (email: string, password: string) => {
    // In production, call API
    // const response = await api.post('/auth/login', { email, password })
    // Simulate login for demo
    await new Promise(resolve => setTimeout(resolve, 800))

    const demoUser: User = {
      id: 'user-1',
      email,
      username: email.split('@')[0],
      full_name: '演示用户',
      role: 'user'
    }

    const demoToken = 'demo-token-' + Date.now()

    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({
      user: demoUser,
      token: demoToken
    }))

    setAuthState({
      user: demoUser,
      isAuthenticated: true,
      isLoading: false
    })
  }

  const register = async (email: string, username: string, password: string, fullName?: string) => {
    // In production, call API
    // const response = await api.post('/auth/register', { email, username, password, full_name: fullName })
    await new Promise(resolve => setTimeout(resolve, 800))

    const newUser: User = {
      id: 'user-' + Date.now(),
      email,
      username,
      full_name: fullName,
      role: 'user'
    }

    const token = 'demo-token-' + Date.now()

    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({
      user: newUser,
      token
    }))

    setAuthState({
      user: newUser,
      isAuthenticated: true,
      isLoading: false
    })
  }

  const logout = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false
    })
  }

  const updateUser = (updates: Partial<User>) => {
    setAuthState(prev => {
      if (!prev.user) return prev
      const updatedUser = { ...prev.user, ...updates }
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({
        user: updatedUser,
        token: JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || '{}').token
      }))
      return { ...prev, user: updatedUser }
    })
  }

  return (
    <AuthContext.Provider value={{ ...authState, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}