/**
 * Practice Store - Zustand state management for practice sessions
 */
import { create } from 'zustand'
import api, { Scenario, RoleConfig } from '../api/practice'

// Message type
interface MessageItem {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  timestamp: string
}

// Session type
interface PracticeSession {
  id: string
  scenario_id: string
  status: 'preparing' | 'active' | 'completed'
  current_phase: 'opening' | 'discovery' | 'needs' | 'proposal' | 'closing'
  websocket_url: string | null
  first_message: string | null
}

// Phase summary type
interface PhaseSummary {
  phase: string
  content: string
  created_at: string
}

interface PracticeState {
  // Scenario state
  scenarios: Scenario[]
  selectedScenario: Scenario | null
  isLoadingScenarios: boolean
  scenarioError: string | null

  // Role config state
  selectedRoleConfig: RoleConfig | null

  // Session state
  currentSession: PracticeSession | null
  messages: MessageItem[]
  phaseSummaries: PhaseSummary[]

  // Actions
  fetchScenarios: () => Promise<void>
  selectScenario: (scenario: Scenario | null) => void
  setRoleConfig: (config: RoleConfig | null) => void
  startSession: () => Promise<void>
  endSession: () => Promise<void>
  resetSession: () => void

  // Chat actions
  addMessage: (message: Omit<MessageItem, 'id' | 'timestamp'>) => void
  updateMessage: (id: string, updates: Partial<MessageItem>) => void
  updateSessionPhase: (phase: PracticeSession['current_phase']) => void
  addPhaseSummary: (summary: Omit<PhaseSummary, 'created_at'>) => void
}

export const usePracticeStore = create<PracticeState>((set, get) => ({
  // Initial state
  scenarios: [],
  selectedScenario: null,
  isLoadingScenarios: false,
  scenarioError: null,
  selectedRoleConfig: null,
  currentSession: null,
  messages: [],
  phaseSummaries: [],

  // Actions
  fetchScenarios: async () => {
    set({ isLoadingScenarios: true, scenarioError: null })
    try {
      const response = await api.getScenarios({ is_builtin: true })
      set({ scenarios: response.data, isLoadingScenarios: false })
    } catch (error) {
      set({
        scenarioError: error instanceof Error ? error.message : '获取场景列表失败',
        isLoadingScenarios: false
      })
    }
  },

  selectScenario: (scenario) => {
    set({ selectedScenario: scenario })
  },

  setRoleConfig: (config) => {
    set({ selectedRoleConfig: config })
  },

  startSession: async () => {
    const { selectedScenario, selectedRoleConfig } = get()
    if (!selectedScenario || !selectedRoleConfig) {
      set({ scenarioError: '请先选择场景和角色配置' })
      return
    }

    try {
      const response = await api.createSession(selectedScenario.id, selectedRoleConfig)
      set({
        currentSession: {
          id: response.session_id,
          scenario_id: selectedScenario.id,
          status: 'preparing',
          current_phase: 'opening',
          websocket_url: response.websocket_url,
          first_message: response.first_message
        }
      })
    } catch (error) {
      set({
        scenarioError: error instanceof Error ? error.message : '创建会话失败'
      })
    }
  },

  endSession: async () => {
    const { currentSession } = get()
    if (!currentSession) return

    try {
      await api.endSession(currentSession.id)
      set({ currentSession: null, messages: [], phaseSummaries: [] })
    } catch (error) {
      set({
        scenarioError: error instanceof Error ? error.message : '结束会话失败'
      })
    }
  },

  resetSession: () => {
    set({
      selectedScenario: null,
      selectedRoleConfig: null,
      currentSession: null,
      messages: [],
      phaseSummaries: []
    })
  },

  // Chat actions
  addMessage: (message) => {
    const newMessage: MessageItem = {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString()
    }
    set((state) => ({ messages: [...state.messages, newMessage] }))
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      )
    }))
  },

  updateSessionPhase: (phase) => {
    set((state) => ({
      currentSession: state.currentSession
        ? { ...state.currentSession, current_phase: phase }
        : null
    }))
  },

  addPhaseSummary: (summary) => {
    set((state) => ({
      phaseSummaries: [
        ...state.phaseSummaries,
        { ...summary, created_at: new Date().toISOString() }
      ]
    }))
  }
}))