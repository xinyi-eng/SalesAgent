/**
 * AuthContext - Authentication state management
 *
 * 真实调用 /api/v1/auth/{login,register,me}，JWT 存 localStorage，
 * axios 拦截器自动加 Authorization header。
 */
import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import axios from 'axios'
import authApi, { User } from '../api/auth'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>
  logout: () => Promise<void>
  updateUser: (updates: Partial<User>) => void
  refreshUser: () => Promise<void>
  getAccessToken: () => string | null
}

const AuthContext = createContext<AuthContextType | null>(null)

const AUTH_STORAGE_KEY = 'sales_agent_auth'

/**
 * 安装 axios 拦截器：每次请求自动带 Authorization header。
 * 这样所有 /api/v1/* 的受保护接口都能识别当前用户。
 */
function installAxiosAuthInterceptor(getToken: () => string | null) {
  axios.interceptors.request.use((config) => {
    const token = getToken()
    if (token) {
      config.headers = config.headers || {}
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }
    return config
  })
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true
  })

  // 读取持久化的认证信息
  const readStored = (): { user: User; token: string } | null => {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (parsed?.token && parsed?.user) return parsed
    } catch {
      // ignore
    }
    return null
  }

  const writeStored = (user: User, token: string) => {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ user, token }))
  }

  const clearStored = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY)
  }

  const getAccessToken = (): string | null => {
    const stored = readStored()
    return stored?.token || null
  }

  // 初始化：装 axios 拦截器，从 localStorage 恢复登录态，
  // 如果有 token 就异步调 /auth/me 验证有效性
  useEffect(() => {
    installAxiosAuthInterceptor(getAccessToken)

    const stored = readStored()
    if (!stored) {
      setAuthState({ user: null, isAuthenticated: false, isLoading: false })
      return
    }

    // 先乐观恢复，等 /auth/me 验证
    setAuthState({ user: stored.user, isAuthenticated: true, isLoading: true })

    authApi
      .me()
      .then((user) => {
        setAuthState({ user, isAuthenticated: true, isLoading: false })
        writeStored(user, getAccessToken() || '')
      })
      .catch(() => {
        // /me 失败 → token 无效，清除登录态
        clearStored()
        setAuthState({ user: null, isAuthenticated: false, isLoading: false })
      })
  }, [])

  const login = async (email: string, password: string) => {
    const res = await authApi.login({ email, password })
    writeStored(res.user, res.access_token)
    setAuthState({ user: res.user, isAuthenticated: true, isLoading: false })
  }

  const register = async (
    email: string,
    username: string,
    password: string,
    fullName?: string
  ) => {
    const res = await authApi.register({
      email,
      username,
      password,
      full_name: fullName,
    })
    writeStored(res.user, res.access_token)
    setAuthState({ user: res.user, isAuthenticated: true, isLoading: false })
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      // 即便后端失败也要清本地
    }
    clearStored()
    setAuthState({ user: null, isAuthenticated: false, isLoading: false })
  }

  const updateUser = (updates: Partial<User>) => {
    setAuthState((prev) => {
      if (!prev.user) return prev
      const updated = { ...prev.user, ...updates }
      const token = getAccessToken() || ''
      writeStored(updated, token)
      return { ...prev, user: updated }
    })
  }

  const refreshUser = useCallback(async () => {
    try {
      const user = await authApi.me()
      setAuthState((prev) => ({ ...prev, user, isAuthenticated: true, isLoading: false }))
      const token = getAccessToken() || ''
      writeStored(user, token)
    } catch (err) {
      // token 失效
      clearStored()
      setAuthState({ user: null, isAuthenticated: false, isLoading: false })
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        ...authState,
        login,
        register,
        logout,
        updateUser,
        refreshUser,
        getAccessToken,
      }}
    >
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
