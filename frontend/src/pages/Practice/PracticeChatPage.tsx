/**
 * PracticeChatPage - Real-time practice chat page
 *
 * Features:
 * - WebSocket connection for real-time messaging
 * - Phase progress tracking
 * - AI customer persona display
 * - Message history
 * - Phase summary triggers
 *
 * Story: 1.2 语音对话与实时交互
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePracticeStore } from '../../stores/practiceStore'
import { useWebSocket, WebSocketMessage } from '../../hooks/useWebSocket'
import { useAudioStream } from '../../hooks/useAudioStream'
import ChatContainer from '../../components/business/practice/ChatContainer'
import PhaseSummaryModal from '../../components/business/practice/PhaseSummaryModal'
import api, { RoleConfig } from '../../api/practice'

interface MessageItem {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  isSending?: boolean
  timestamp: string
}

interface PhaseSummaryData {
  phase: string
  phase_label: string
  good_points: string[]
  improvements: string[]
  suggestions: string[]
}

const PracticeChatPage = () => {
  const navigate = useNavigate()
  const {
    currentSession,
    selectedScenario,
    selectedRoleConfig,
    messages,
    updateMessage,
    updateSessionPhase,
    phaseSummaries,
    addPhaseSummary
  } = usePracticeStore()

  const [messages_, setMessages_] = useState<MessageItem[]>([])
  const [aiAudioData, setAiAudioData] = useState<Uint8Array | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [isSummaryModalOpen, setIsSummaryModalOpen] = useState(false)
  const [currentPhaseSummary, setCurrentPhaseSummary] = useState<PhaseSummaryData | null>(null)
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)

  // Audio streaming for TTS playback
  const audioStream = useAudioStream()

  // Initialize with first AI message when session starts
  useEffect(() => {
    if (currentSession?.first_message && messages_.length === 0) {
      const firstMsg: MessageItem = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: 'ai',
        content: currentSession.first_message,
        timestamp: new Date().toISOString()
      }
      setMessages_([firstMsg])
    }
  }, [currentSession?.first_message])

  // Build WebSocket URL
  const wsUrl = currentSession?.id
    ? `${import.meta.env.VITE_WS_URL || 'ws://localhost:8001'}/ws/practice/${currentSession.id}`
    : null

  const handleMessage = useCallback((wsMessage: WebSocketMessage) => {
    // Handle different message types from WebSocket
    if (wsMessage.type === 'user_message') {
      // User's own message - already added locally
      return
    }

    if (wsMessage.type === 'ai_message' || wsMessage.type === 'ai_streaming_end') {
      // Final AI message
      const content = wsMessage.content || wsMessage.data?.content as string || ''
      if (content) {
        const newMessage: MessageItem = {
          id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'ai',
          content: content,
          timestamp: wsMessage.timestamp || new Date().toISOString()
        }
        setMessages_(prev => [...prev, newMessage])
      }
    } else if (wsMessage.type === 'ai_streaming_update') {
      // Incremental streaming update - update the last AI message
      const contentPrefix = wsMessage.content || wsMessage.data?.content_prefix as string || ''
      if (contentPrefix) {
        setMessages_(prev => {
          const lastMsg = prev[prev.length - 1]
          if (lastMsg && lastMsg.type === 'ai') {
            return [...prev.slice(0, -1), { ...lastMsg, content: contentPrefix }]
          }
          return [...prev, {
            id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type: 'ai' as const,
            content: contentPrefix,
            timestamp: wsMessage.timestamp || new Date().toISOString()
          }]
        })
      }
    }

    // Handle phase completion
    if (wsMessage.type === 'phase_complete') {
      updateSessionPhase(wsMessage.data?.phase as string || 'discovery')
    }

    // Handle backchannel (listening acknowledgment)
    if (wsMessage.type === 'backchannel') {
      console.log('[Backchannel]', wsMessage.content)
    }
  }, [updateSessionPhase])

  const handleConnected = useCallback(() => {
    console.log('WebSocket connected')
    // Send initial context to AI
    if (selectedScenario && selectedRoleConfig) {
      // Session context will be handled by backend
    }
  }, [selectedScenario, selectedRoleConfig])

  const handleDisconnected = useCallback(() => {
    console.log('WebSocket disconnected')
  }, [])

  const { isConnected, sendMessage: wsSendMessage, lastAudioChunk } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    onAudioChunk: (chunk) => {
      // Store the audio chunk for playback
      setAiAudioData(chunk)
      // Play audio immediately when received
      audioStream.playChunk(chunk)
    },
    onConnected: handleConnected,
    onDisconnected: handleDisconnected
  })

  const handleSendMessage = useCallback((content: string) => {
    // Add user message to local state
    const userMsg: MessageItem = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'user',
      content,
      isSending: true,
      timestamp: new Date().toISOString()
    }
    setMessages_(prev => [...prev, userMsg])

    setIsSending(true)

    // Send via WebSocket
    wsSendMessage(content)

    // Update message status to show sending
    setMessages_(prev => prev.map(m =>
      m.id === userMsg.id ? { ...m, isSending: false } : m
    ))
    setIsSending(false)
  }, [wsSendMessage])

  // Get role configuration labels
  const getRoleLabel = (config: RoleConfig | null, key: keyof RoleConfig) => {
    if (!config?.[key]) return ''
    const labels: Record<string, Record<string, string>> = {
      position_level: { junior: '初级客户经理', middle: '中级采购经理', senior: '高级总监' },
      personality: { rational: '理性型', emotional: '感性型', hesitant: '犹豫型', decisive: '果断型' },
      decision_style: { price_oriented: '价格导向', value_oriented: '价值导向', relationship_oriented: '关系导向', risk_averse: '风险规避' }
    }
    return labels[key]?.[config[key] as string] || config[key] as string
  }

  // Handle phase summary request
  const handleGetPhaseSummary = useCallback(async () => {
    if (!currentSession?.id || !currentSession?.current_phase) return

    setIsSummaryModalOpen(true)
    setIsSummaryLoading(true)
    setCurrentPhaseSummary(null)

    try {
      // Call the actual API
      const response = await api.getPhaseSummary(currentSession.id, currentSession.current_phase)
      setCurrentPhaseSummary(response)
    } catch (error) {
      console.error('Failed to get phase summary:', error)
      // Fallback to minimal demo data on error
      setCurrentPhaseSummary({
        phase: currentSession.current_phase,
        phase_label: ['开场破冰', '需求挖掘', '方案呈现', '促成成交', '复盘总结'][
          ['opening', 'discovery', 'needs', 'proposal', 'closing'].indexOf(currentSession.current_phase)
        ] || currentSession.current_phase,
        overall_score: 0,
        situation_score: 0,
        problem_score: 0,
        implication_score: 0,
        need_payoff_score: 0,
        good_points: ['数据加载失败，请重试'],
        improvements: ['后端API调用失败'],
        suggestions: ['请检查后端服务是否正常运行']
      })
    } finally {
      setIsSummaryLoading(false)
    }
  }, [currentSession])

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/practice')}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="font-semibold text-gray-900">{selectedScenario?.name || '对练中'}</h1>
            <p className="text-xs text-gray-500">
              {isConnected ? (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-success rounded-full" />
                  已连接
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                  连接中...
                </span>
              )}
            </p>
          </div>
        </div>

        {/* AI Customer Persona */}
        {selectedRoleConfig && (
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-lg">
            <div className="w-10 h-10 bg-secondary/10 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div className="text-sm">
              <p className="font-medium text-gray-900">
                {getRoleLabel(selectedRoleConfig, 'position_level')}
              </p>
              <p className="text-gray-500">
                {getRoleLabel(selectedRoleConfig, 'personality')} · {getRoleLabel(selectedRoleConfig, 'decision_style')}
              </p>
            </div>
          </div>
        )}
      </header>

      {/* Phase Progress */}
      <div className="bg-white border-b border-gray-200 px-4 py-2">
        <div className="flex items-center gap-2 overflow-x-auto">
          <PhaseIndicator
            label="开场破冰"
            isActive={currentSession?.current_phase === 'opening'}
            isCompleted={['discovery', 'needs', 'proposal', 'closing'].includes(currentSession?.current_phase || '')}
          />
          <div className="w-8 h-0.5 bg-gray-200" />
          <PhaseIndicator
            label="需求挖掘"
            isActive={currentSession?.current_phase === 'discovery'}
            isCompleted={['needs', 'proposal', 'closing'].includes(currentSession?.current_phase || '')}
          />
          <div className="w-8 h-0.5 bg-gray-200" />
          <PhaseIndicator
            label="方案呈现"
            isActive={currentSession?.current_phase === 'needs'}
            isCompleted={['proposal', 'closing'].includes(currentSession?.current_phase || '')}
          />
          <div className="w-8 h-0.5 bg-gray-200" />
          <PhaseIndicator
            label="促成成交"
            isActive={currentSession?.current_phase === 'proposal'}
            isCompleted={currentSession?.current_phase === 'closing'}
          />
          <div className="w-8 h-0.5 bg-gray-200" />
          <PhaseIndicator
            label="复盘总结"
            isActive={currentSession?.current_phase === 'closing'}
            isCompleted={false}
          />
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <ChatContainer
          messages={messages_}
          onSendMessage={handleSendMessage}
          isDisabled={currentSession?.status === 'completed'}
          isSending={isSending}
          isConnected={isConnected}
        />
      </div>

      {/* Summary Button */}
      <div className="bg-white border-t border-gray-200 px-4 py-3 flex justify-between items-center">
        <div className="text-sm text-gray-500">
          当前阶段: <span className="font-medium text-primary">
            {currentSession?.current_phase === 'opening' && '开场破冰'}
            {currentSession?.current_phase === 'discovery' && '需求挖掘'}
            {currentSession?.current_phase === 'needs' && '方案呈现'}
            {currentSession?.current_phase === 'proposal' && '促成成交'}
            {currentSession?.current_phase === 'closing' && '复盘总结'}
          </span>
        </div>
        <button
          onClick={handleGetPhaseSummary}
          disabled={currentSession?.status === 'completed'}
          className="px-4 py-2 bg-secondary text-white rounded-lg hover:bg-secondary/90 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-all"
        >
          生成阶段总结
        </button>
      </div>

      {/* Phase Summary Modal */}
      <PhaseSummaryModal
        isOpen={isSummaryModalOpen}
        onClose={() => setIsSummaryModalOpen(false)}
        summary={currentPhaseSummary}
        isLoading={isSummaryLoading}
        sessionId={currentSession?.id}
      />
    </div>
  )
}

const PhaseIndicator = ({ label, isActive, isCompleted }: { label: string; isActive: boolean; isCompleted: boolean }) => (
  <div className="flex items-center gap-2">
    <div className={`
      w-6 h-6 rounded-full flex items-center justify-center text-xs
      ${isCompleted ? 'bg-success text-white' : isActive ? 'bg-primary text-white' : 'bg-gray-200 text-gray-500'}
    `}>
      {isCompleted ? (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <span className="font-medium">{label[0]}</span>
      )}
    </div>
    <span className={`text-sm whitespace-nowrap ${isActive ? 'text-primary font-medium' : 'text-gray-500'}`}>
      {label}
    </span>
  </div>
)

export default PracticeChatPage