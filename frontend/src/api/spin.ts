/**
 * SPIN API Client
 */
import axios from 'axios'

const API_BASE = '/api/v1'

export interface CompanyInfo {
  subject_type: 'company'
  background: string
  recent_news: string[]
  competitors: string[]
  potential_pains: string[]
  extra_info: Record<string, unknown>
}

export interface PersonInfo {
  subject_type: 'person'
  name: string
  title: string
  company: string
  background: string
  recent_activities: string[]
  potential_pains: string[]
  extra_info: Record<string, unknown>
}

export type InvestigationResult = CompanyInfo | PersonInfo

export interface CustomerContext {
  industry: string
  scale: string
  pain_points: string[]
}

export interface SpinQuestionsRequest {
  customer: CustomerContext
}

export interface SpinQuestionList {
  question_list_id: string
  situation_questions: string[]
  problem_questions: string[]
  implication_questions: string[]
  need_payoff_questions: string[]
  customer_context: CustomerContext
  created_at: string
}

export interface SpinQuestionResponse {
  success: boolean
  data?: SpinQuestionList
  error?: string
}

export const spinApi = {
  /**
   * 调查客户信息（公司或个人）
   */
  async investigate(customerName: string): Promise<InvestigationResult> {
    const response = await axios.post<{success: boolean; data?: InvestigationResult; error?: string}>(
      `${API_BASE}/spin/investigate`,
      { customer_name: customerName }
    )
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || '调查失败')
    }
    return response.data.data
  },

  /**
   * 生成SPIN问题清单
   */
  async generateQuestions(customer: CustomerContext): Promise<SpinQuestionList> {
    const response = await axios.post<SpinQuestionResponse>(`${API_BASE}/spin/questions`, {
      customer
    })
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || '生成失败')
    }
    return response.data.data
  },

  /**
   * 获取问题清单
   */
  async getQuestions(questionListId: string): Promise<SpinQuestionList> {
    const response = await axios.get<SpinQuestionResponse>(`${API_BASE}/spin/questions/${questionListId}`)
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || '获取失败')
    }
    return response.data.data
  },

  /**
   * 获取最新问题清单
   */
  async getLatestQuestions(): Promise<SpinQuestionList | null> {
    const response = await axios.get<SpinQuestionResponse>(`${API_BASE}/spin/questions`)
    if (response.data.success && response.data.data) {
      return response.data.data
    }
    return null
  }
}

export default spinApi
