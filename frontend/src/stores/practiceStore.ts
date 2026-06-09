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
  audioData?: string  // base64 encoded audio for replay
  timestamp: string
}

// Customer persona (specific character, dynamically generated)
export interface CustomerPersona {
  name: string
  gender?: string
  age_range?: string
  title: string
  company: string
  industry?: string
  company_size?: string
  background?: string
  current_situation?: string
  pain_points?: string[]
  concerns?: string[]
  personality_traits?: string
  speaking_style?: string
  scenario_context?: string
  recent_activities?: string
}

// Session type
interface PracticeSession {
  id: string
  scenario_id: string
  status: 'preparing' | 'active' | 'completed'
  current_phase: 'opening' | 'discovery' | 'needs' | 'proposal' | 'closing'
  websocket_url: string | null
  first_message: string | null
  persona: CustomerPersona | null
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
  startSession: (spinContext?: {
    customerContext?: any
    investigationResult?: any
    userContext?: any
  }) => Promise<void>
  endSession: () => Promise<void>
  resetSession: () => void

  // Chat actions
  addMessage: (message: Omit<MessageItem, 'id' | 'timestamp'>) => void
  updateMessage: (id: string, updates: Partial<MessageItem>) => void
  updateSessionPhase: (phase: PracticeSession['current_phase']) => void
  updatePersona: (persona: CustomerPersona) => void
  addPhaseSummary: (summary: Omit<PhaseSummary, 'created_at'>) => void
}

// Manually persist currentSession to sessionStorage
// (simple wrapper, avoids zustand persist middleware version issues)
const SESSION_KEY = 'sales-agent-practice-session'

function loadPersistedSession(): PracticeSession | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    return JSON.parse(raw) as PracticeSession
  } catch {
    return null
  }
}

function savePersistedSession(session: PracticeSession | null) {
  try {
    if (session) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    } else {
      sessionStorage.removeItem(SESSION_KEY)
    }
  } catch {
    // ignore
  }
}

export const usePracticeStore = create<PracticeState>()(
  (set, get) => ({
  // Initial state
  scenarios: [],
  selectedScenario: null,
  isLoadingScenarios: false,
  scenarioError: null,
  selectedRoleConfig: null,
  currentSession: loadPersistedSession(),  // restore from sessionStorage
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

  startSession: async (spinContext?: {
    customerContext?: any
    investigationResult?: any
    userContext?: any
  }) => {
    const { selectedScenario, selectedRoleConfig } = get()
    if (!selectedScenario || !selectedRoleConfig) {
      set({ scenarioError: '请先选择场景和角色配置' })
      return
    }

    try {
      const response = await api.createSession(
        selectedScenario.id,
        selectedRoleConfig,
        spinContext?.customerContext,
        spinContext?.investigationResult,
        spinContext?.userContext
      )
      set({
        currentSession: {
          id: response.session_id,
          scenario_id: selectedScenario.id,
          status: 'preparing',
          current_phase: 'opening',
          websocket_url: response.websocket_url,
          first_message: response.first_message,
          persona: spinContext?.investigationResult
            ? {
                name: spinContext.investigationResult.name || '客户',
                title: spinContext.investigationResult.title || '',
                company: spinContext.investigationResult.company || '',
                background: spinContext.investigationResult.background,
                pain_points: spinContext.investigationResult.potential_pains,
              }
            : null
        }
      })
      // Persist
      const newSession = get().currentSession
      savePersistedSession(newSession)
    } catch (error) {
      set({
        scenarioError: error instanceof Error ? error.message : '创建会话失败'
      })
    }
  },

  updatePersona: (persona: CustomerPersona) => {
    set(state => ({
      currentSession: state.currentSession
        ? { ...state.currentSession, persona }
        : null
    }))
    savePersistedSession(get().currentSession)
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
  })
)