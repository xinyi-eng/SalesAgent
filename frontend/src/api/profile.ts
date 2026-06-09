/**
 * Profile API Client — user profile and stats
 *
 * Note: backend mounts these under /users (not /profile).
 * See backend/app/api/v1/profile.py
 */
import axios from 'axios'

const API_BASE = '/api/v1/users'

export interface SkillLevel {
  skill_name: string
  level: number  // 1-5
  last_updated?: string
}

export interface UserProfileStats {
  total_sessions: number
  total_messages: number
  total_duration_minutes: number
  avg_score: number
  phases_mastered: string[]
  skills: SkillLevel[]
}

export interface UserProfile {
  user_id: string
  email: string
  username: string
  full_name: string | null
  phone: string | null
  avatar_url: string | null
  bio: string | null
  role: string
  joined_at: string
  last_login_at: string | null
  stats: UserProfileStats
}

export interface UserStats {
  total_practice_sessions: number
  total_practice_time: number  // minutes
  average_scores: Record<string, number>  // e.g. {communication: 80, persuasion: 75, ...}
  recent_improvement: number  // percent
  strongest_skill: string
  weakest_skill: string
  phase_progress: Record<string, number>
}

const api = {
  async getProfile(): Promise<UserProfile> {
    const res = await axios.get(`${API_BASE}/me/profile`)
    return res.data
  },

  async getStats(): Promise<UserStats> {
    const res = await axios.get(`${API_BASE}/me/stats`)
    return res.data
  },

  async updateSkills(updates: { skill_name: string; level: number }[]): Promise<SkillLevel[]> {
    const res = await axios.put(`${API_BASE}/me/skills`, updates)
    return res.data
  },

  async uploadAvatar(avatarUrl: string): Promise<{ avatar_url: string }> {
    const res = await axios.post(`${API_BASE}/me/avatar`, { avatar_url: avatarUrl })
    return res.data
  },
}

export default api
