/**
 * SPIN Store - Zustand state management for SPIN preparation
 */
import { create } from 'zustand'
import { spinApi, CustomerContext, SpinQuestionList } from '../api/spin'

interface SpinState {
  // 客户背景
  customerContext: CustomerContext | null
  setCustomerContext: (context: CustomerContext) => void

  // 问题清单
  questionList: SpinQuestionList | null
  setQuestionList: (list: SpinQuestionList) => void

  // 状态
  isGenerating: boolean
  error: string | null

  // 操作
  generateQuestions: () => Promise<void>
  clearQuestions: () => void
}

export const useSpinStore = create<SpinState>((set, get) => ({
  customerContext: null,
  questionList: null,
  isGenerating: false,
  error: null,

  setCustomerContext: (context) => {
    set({ customerContext: context, error: null })
  },

  setQuestionList: (list) => {
    set({ questionList: list })
  },

  generateQuestions: async () => {
    const { customerContext } = get()
    if (!customerContext) {
      set({ error: '请先填写客户背景' })
      return
    }

    set({ isGenerating: true, error: null })

    try {
      const questionList = await spinApi.generateQuestions(customerContext)
      set({ questionList, isGenerating: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '生成失败',
        isGenerating: false
      })
    }
  },

  clearQuestions: () => {
    set({
      questionList: null,
      error: null
    })
  }
}))

export default useSpinStore
