/**
 * Practice API Client
 */
import axios from 'axios'

const API_BASE = '/api/v1'

export interface Scenario {
  id: string
  name: string
  description: string
  type: string
  category: string
  sub_category: string
  default_role_config: object
  is_builtin: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface RoleConfig {
  position_level: string
  personality: string
  decision_style: string
  voice: string  // TTS voice_id for AI customer
}

export interface SessionCreateResponse {
  session_id: string
  websocket_url: string
  first_message: string
}

// Session list types
export interface SessionListItem {
  id: string
  scenario_id: string
  scenario_name: string | null
  scenario_type: string | null
  user_id: string | null
  role_config: RoleConfig
  status: 'preparing' | 'active' | 'completed'
  current_phase: string | null
  score: number | null
  message_count: number
  duration_minutes: number
  created_at: string
  ended_at: string | null
}

export interface SessionListResponse {
  data: SessionListItem[]
  total: number
  page: number
  page_size: number
}

// Dashboard stats types
export interface DashboardStats {
  total_sessions: number
  total_time_minutes: number
  avg_score: number | null
  improvement_rate: number
  this_week_sessions: number
  this_week_time: number
  this_week_score: number | null
  streak_days: number
}

// History stats types
export interface HistoryStats {
  sessions: number
  completed: number
  duration_minutes: number
  messages: number
  avg_score: number | null
}

export interface HistoryStatsResponse {
  last_30_days: HistoryStats
  last_90_days: HistoryStats
}

// Session summary types
export interface SessionSummary {
  session_id: string
  overall_score: number
  situation_score: number
  problem_score: number
  implication_score: number
  need_payoff_score: number
  key_strengths: string[]
  areas_for_improvement: string[]
  next_practice_focus: string
}

// Phase summary types
export interface PhaseSummary {
  phase: string
  phase_label: string
  overall_score: number
  situation_score: number
  problem_score: number
  implication_score: number
  need_payoff_score: number
  good_points: string[]
  improvements: string[]
  suggestions: string[]
}

const api = {
  /**
   * 获取场景列表
   */
  async getScenarios(params?: {
    category?: string
    sub_category?: string
    type?: string
    is_builtin?: boolean
  }): Promise<{ data: Scenario[]; total: number }> {
    const response = await axios.get(`${API_BASE}/practice/scenarios`, { params })
    return response.data
  },

  /**
   * 获取单个场景
   */
  async getScenario(scenarioId: string): Promise<Scenario> {
    const response = await axios.get(`${API_BASE}/practice/scenarios/${scenarioId}`)
    return response.data
  },

  /**
   * 创建对练会话
   */
  async createSession(
    scenarioId: string,
    roleConfig: RoleConfig,
    customerContext?: any,
    investigationResult?: any,
    userContext?: any
  ): Promise<SessionCreateResponse> {
    const response = await axios.post(`${API_BASE}/practice/sessions`, {
      scenario_id: scenarioId,
      role_config: roleConfig,
      customer_context: customerContext,
      investigation_result: investigationResult,
      user_context: userContext,
    })
    return response.data
  },

  /**
   * 结束对练会话
   */
  async endSession(sessionId: string): Promise<void> {
    await axios.post(`${API_BASE}/practice/sessions/${sessionId}/end`)
  },

  /**
   * 获取会话总结报告
   */
  async getSessionSummary(sessionId: string): Promise<SessionSummary> {
    const response = await axios.get(`${API_BASE}/practice/sessions/${sessionId}/summary`)
    return response.data
  },

  /**
   * 下载会话报告 PDF（触发浏览器下载）
   */
  async downloadReportPdf(sessionId: string): Promise<void> {
    const response = await axios.get(
      `${API_BASE}/practice/sessions/${sessionId}/report/pdf`,
      { responseType: 'blob' }
    )
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `salesagent-report-${sessionId.slice(0, 8)}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  /**
   * 获取会话列表（分页）
   */
  async getSessions(params?: {
    page?: number
    page_size?: number
    status?: string
    scenario_type?: string
  }): Promise<SessionListResponse> {
    const response = await axios.get(`${API_BASE}/practice/sessions-list`, { params })
    return response.data
  },

  /**
   * 获取仪表盘统计
   */
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await axios.get(`${API_BASE}/practice/dashboard/stats`)
    return response.data
  },

  /**
   * 获取历史统计
   */
  async getHistoryStats(): Promise<HistoryStatsResponse> {
    const response = await axios.get(`${API_BASE}/practice/history/stats`)
    return response.data
  },

  /**
   * 获取单个会话详情
   */
  async getSession(sessionId: string): Promise<any> {
    const response = await axios.get(`${API_BASE}/practice/sessions/${sessionId}`)
    return response.data
  },

  /**
   * 获取阶段总结
   */
  async getPhaseSummary(sessionId: string, phase: string): Promise<PhaseSummary> {
    const response = await axios.post(`${API_BASE}/practice/sessions/${sessionId}/phases/${phase}/summary`)
    return response.data
  }
}

export default api