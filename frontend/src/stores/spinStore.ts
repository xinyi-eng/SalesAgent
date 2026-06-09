/**
 * SPIN Store - Zustand state management for SPIN preparation
 */
import { create } from 'zustand'
import { spinApi, CustomerContext, SpinQuestionList, InvestigationResult } from '../api/spin'

interface SpinState {
  // 步骤
  currentStep: 'info' | 'investigation' | 'pain_points' | 'questions'
  setCurrentStep: (step: 'info' | 'investigation' | 'pain_points' | 'questions') => void

  // 客户基本信息
  customerName: string
  setCustomerName: (name: string) => void
  customerContext: CustomerContext | null
  setCustomerContext: (context: CustomerContext) => void

  // 调查状态
  isInvestigating: boolean
  investigationResult: InvestigationResult | null
  investigateError: string | null
  investigate: (customerName: string) => Promise<void>

  // 痛点确认
  confirmedPains: string[]
  togglePain: (pain: string) => void
  addCustomPain: (pain: string) => void
  removePain: (pain: string) => void

  // 问题清单
  questionList: SpinQuestionList | null
  isGenerating: boolean
  generateError: string | null
  generateQuestions: () => Promise<void>

  // 清理
  reset: () => void
}

export const useSpinStore = create<SpinState>((set, get) => ({
  currentStep: 'info',
  setCurrentStep: (step) => set({ currentStep: step }),

  customerName: '',
  setCustomerName: (name) => set({ customerName: name }),

  customerContext: null,
  setCustomerContext: (context) => set({ customerContext: context }),

  isInvestigating: false,
  investigationResult: null,
  investigateError: null,
  investigate: async (customerName) => {
    if (!customerName.trim()) {
      set({ investigateError: '请输入客户名称' })
      return
    }

    set({ isInvestigating: true, investigateError: null, investigationResult: null })

    try {
      // Step 1: 先调用后端 MCP 搜索接口获取网络上下文
      let searchContext = ''
      try {
        const searchResp = await fetch('/api/v1/spin/web-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: customerName })
        })
        const searchData = await searchResp.json()
        if (searchData.success && searchData.context) {
          searchContext = searchData.context
        }
      } catch {
        // 搜索失败则跳过，继续用LLM知识
      }

      // Step 2: 调用后端调查API（带上搜索上下文）
      const response = await fetch('/api/v1/spin/investigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_name: customerName, search_context: searchContext })
      })

      const result = await response.json()

      if (result.success && result.data) {
        set({
          investigationResult: result.data,
          isInvestigating: false,
          currentStep: 'investigation'
        })
      } else {
        set({
          investigateError: result.error || '调查失败',
          isInvestigating: false
        })
      }
    } catch (error) {
      set({
        investigateError: error instanceof Error ? error.message : '调查失败',
        isInvestigating: false
      })
    }
  },

  confirmedPains: [],
  togglePain: (pain) => {
    const { confirmedPains } = get()
    if (confirmedPains.includes(pain)) {
      set({ confirmedPains: confirmedPains.filter(p => p !== pain) })
    } else {
      set({ confirmedPains: [...confirmedPains, pain] })
    }
  },
  addCustomPain: (pain) => {
    const { confirmedPains } = get()
    if (!confirmedPains.includes(pain)) {
      set({ confirmedPains: [...confirmedPains, pain] })
    }
  },
  removePain: (pain) => {
    set({ confirmedPains: get().confirmedPains.filter(p => p !== pain) })
  },

  questionList: null,
  isGenerating: false,
  generateError: null,
  generateQuestions: async () => {
    const { customerContext } = get()
    if (!customerContext) {
      set({ generateError: '请先填写客户背景' })
      return
    }

    set({ isGenerating: true, generateError: null })

    try {
      const questionList = await spinApi.generateQuestions(customerContext)
      set({
        questionList,
        isGenerating: false,
        currentStep: 'questions'
      })
    } catch (error) {
      set({
        generateError: error instanceof Error ? error.message : '生成失败',
        isGenerating: false
      })
    }
  },

  reset: () => set({
    currentStep: 'info',
    customerName: '',
    customerContext: null,
    isInvestigating: false,
    investigationResult: null,
    investigateError: null,
    confirmedPains: [],
    questionList: null,
    isGenerating: false,
    generateError: null
  })
}))

export default useSpinStore
