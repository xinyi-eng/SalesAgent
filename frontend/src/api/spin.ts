/**
 * SPIN API Client
 */
import api from './index'

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
   * 生成SPIN问题清单
   */
  async generateQuestions(customer: CustomerContext): Promise<SpinQuestionList> {
    const response = await api.post<SpinQuestionResponse>('/spin/questions', {
      customer
    })
    if (!response.success || !response.data) {
      throw new Error(response.error || '生成失败')
    }
    return response.data
  },

  /**
   * 获取问题清单
   */
  async getQuestions(questionListId: string): Promise<SpinQuestionList> {
    const response = await api.get<SpinQuestionResponse>(`/spin/questions/${questionListId}`)
    if (!response.success || !response.data) {
      throw new Error(response.error || '获取失败')
    }
    return response.data
  },

  /**
   * 获取最新问题清单
   */
  async getLatestQuestions(): Promise<SpinQuestionList | null> {
    const response = await api.get<SpinQuestionResponse>('/spin/questions')
    if (response.success && response.data) {
      return response.data
    }
    return null
  }
}

export default spinApi
