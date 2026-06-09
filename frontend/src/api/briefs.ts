/**
 * Brief API Client — Industry Briefs
 */
import axios from 'axios'

const API_BASE = '/api/v1'

export interface BriefItem {
  title: string
  url: string                  // 原文链接（真实）
  source: string
  source_level: string        // L1/L2/L3/L4
  summary: string
  date?: string                // 兼容旧版
  published_at?: string        // ISO8601 新版
  relevance: number
}

export interface BriefSummary {
  id: string
  title: string
  industry: string | null
  keywords: string | null
  item_count: number
  takeaway_count: number
  status: string
  created_at: string
}

export interface BriefDetail extends BriefSummary {
  summary: string | null
  items: BriefItem[]
  key_takeaways: string[]
  error: string | null
}

export interface BriefGenerateRequest {
  industry: string
  keywords?: string
  title?: string
}

export interface BriefSubscription {
  industry: string
  keywords: string
}

export interface BriefSubscriptionsUpdate {
  subscriptions: BriefSubscription[]
}

export interface TodayBriefs {
  date: string
  industries: Record<string, BriefSummary[]>
}

export const INDUSTRY_OPTIONS = [
  '制造业', '科技软件', '金融', '医疗健康',
  '教育培训', '零售电商', '建筑工程', '物流运输',
  '能源化工', '通用',
]

const api = {
  async listBriefs(): Promise<BriefSummary[]> {
    const response = await axios.get(`${API_BASE}/briefs`)
    return response.data
  },

  async getBrief(id: string): Promise<BriefDetail> {
    const response = await axios.get(`${API_BASE}/briefs/${id}`)
    return response.data
  },

  async generateBrief(req: BriefGenerateRequest): Promise<BriefDetail> {
    const response = await axios.post(`${API_BASE}/briefs/generate`, req)
    return response.data
  },

  async deleteBrief(id: string): Promise<void> {
    await axios.delete(`${API_BASE}/briefs/${id}`)
  },

  pdfUrl(id: string): string {
    return `${API_BASE}/briefs/${id}/pdf`
  },

  async getToday(): Promise<TodayBriefs> {
    const response = await axios.get(`${API_BASE}/briefs/today`)
    return response.data
  },

  async getSubscriptions(): Promise<BriefSubscriptionsUpdate> {
    const response = await axios.get(`${API_BASE}/briefs/subscriptions`)
    return response.data
  },

  async updateSubscriptions(payload: BriefSubscriptionsUpdate): Promise<BriefSubscriptionsUpdate> {
    const response = await axios.put(`${API_BASE}/briefs/subscriptions`, payload)
    return response.data
  },

  async refreshBriefs(): Promise<BriefSummary[]> {
    const response = await axios.post(`${API_BASE}/briefs/refresh`)
    return response.data
  },

  levelColor(level: string): { bg: string; text: string; label: string } {
    const map: Record<string, { bg: string; text: string; label: string }> = {
      L1: { bg: 'bg-green-100', text: 'text-green-700', label: 'L1 权威官方' },
      L2: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'L2 权威媒体' },
      L3: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'L3 行业垂直' },
      L4: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'L4 社交舆情' },
    }
    return map[level] || { bg: 'bg-gray-100', text: 'text-gray-600', label: level || '未分级' }
  },
}

export default api
