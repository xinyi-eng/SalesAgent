/**
 * Auth API Client — login, register, profile
 */
import axios from 'axios'

const API_BASE = '/api/v1'

export interface User {
  id: string
  email: string
  username: string
  full_name?: string | null
  phone?: string | null
  avatar_url?: string | null
  bio?: string | null
  industry?: string | null
  role: string
  is_active: boolean
  created_at?: string
  last_login_at?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface RegisterPayload {
  email: string
  username: string
  password: string
  full_name?: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface UpdateMePayload {
  email?: string
  username?: string
  full_name?: string
  phone?: string
  bio?: string
}

const api = {
  async register(payload: RegisterPayload): Promise<TokenResponse> {
    const res = await axios.post(`${API_BASE}/auth/register`, payload)
    return res.data
  },

  async login(payload: LoginPayload): Promise<TokenResponse> {
    const res = await axios.post(`${API_BASE}/auth/login`, payload)
    return res.data
  },

  async refresh(refreshToken: string): Promise<TokenResponse> {
    const res = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken })
    return res.data
  },

  async me(): Promise<User> {
    const res = await axios.get(`${API_BASE}/auth/me`)
    return res.data
  },

  async updateMe(payload: UpdateMePayload): Promise<User> {
    const res = await axios.put(`${API_BASE}/auth/me`, payload)
    return res.data
  },

  async logout(): Promise<void> {
    await axios.post(`${API_BASE}/auth/logout`)
  },
}

export default api
