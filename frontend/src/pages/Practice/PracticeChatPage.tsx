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
import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePracticeStore } from '../../stores/practiceStore'
import { useWebSocket, StreamMessage } from '../../hooks/useWebSocket'
import { useAudioStream } from '../../hooks/useAudioStream'
import ChatContainer from '../../components/business/practice/ChatContainer'
import PhaseSummaryModal from '../../components/business/practice/PhaseSummaryModal'
import SpinStageHint from '../../components/business/practice/SpinStageHint'
import api, { RoleConfig } from '../../api/practice'

interface MessageItem {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  audioData?: string  // base64 encoded audio for replay
  isSending?: boolean
  timestamp: string
  knowledgeRefs?: Array<{
    category?: string
    source?: string
    chapter?: string
    section?: string
    excerpt?: string
    relevance?: number
  }>
}

interface PhaseSummaryData {
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

const VALID_PHASES = ['opening', 'discovery', 'needs', 'proposal', 'closing'] as const

const PracticeChatPage = () => {
  const navigate = useNavigate()
  const {
    currentSession,
    selectedScenario,
    selectedRoleConfig,
    updateSessionPhase,
    updatePersona
  } = usePracticeStore()

  const [messages_, setMessages_] = useState<MessageItem[]>([])
  const [isSending, setIsSending] = useState(false)
  const [isSummaryModalOpen, setIsSummaryModalOpen] = useState(false)
  const [currentPhaseSummary, setCurrentPhaseSummary] = useState<PhaseSummaryData | null>(null)
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)

  // Track current AI message ID for audio chunk accumulation
  const currentAIMessageIdRef = useRef<string | null>(null)

  // Audio streaming for TTS playback
  const audioStream = useAudioStream()

  // First message comes from WebSocket (ai_message with empty audio_data,
// then ai_message_audio with the audio). No local fallback - backend
// always sends it.

  // 销售员自填的练习档案（从 practiceStore 传过来，banner 展示用）
  const userContext = (selectedRoleConfig as any)?.__userContext as
    | {
        sales_level?: string
        years_experience?: number
        practice_goals?: string[]
        difficulty?: string
        notes?: string
      }
    | undefined

  // Wait for session to be loaded from store before deciding to redirect.
  // On first render, currentSession may be null while zustand rehydrates,
  // so we wait one tick before redirecting to avoid an infinite navigation loop.
  const [hasCheckedSession, setHasCheckedSession] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setHasCheckedSession(true), 100)
    return () => clearTimeout(timer)
  }, [])
  useEffect(() => {
    if (hasCheckedSession && !currentSession?.id) {
      navigate('/practice')
    }
  }, [hasCheckedSession, currentSession, navigate])

  // Build WebSocket URL - 走 vite 代理（同页同源，自动跟随 vite.config.ts 的 target）
  // 这样切换后端端口只改一处；硬编码 ws://localhost:8001 之前会绕过 proxy
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = currentSession?.id && currentSession.id.length > 10
    ? `${wsProtocol}//${window.location.host}/ws/practice/${currentSession.id}`
    : null

  const handleMessage = useCallback((wsMessage: StreamMessage) => {
    // Handle different message types from WebSocket
    if (wsMessage.type === 'user_message') {
      // User's own message - already added locally
      return
    }

    // Backend confirms the user message and includes the ASR transcript
    // (so the local bubble can be updated with the canonical Chinese text).
    if (wsMessage.type === 'user_message_ack') {
      const targetId = wsMessage.id
      const asrText = (wsMessage.data?.asr_text as string)
        || (wsMessage as any).asr_text
        || ''
      const asrOk = (wsMessage.data?.asr_ok as boolean)
        ?? (wsMessage as any).asr_ok
        ?? false
      console.log('[ACK] msg keys:', Object.keys(wsMessage), 'id:', wsMessage.id, 'data:', wsMessage.data, 'asr_text:', (wsMessage as any).asr_text)
      // Replace the bubble content whenever the backend gives us text.
      // - If ASR succeeded (asrOk=true), the bubble gets the real transcript.
      // - If ASR failed (asrOk=false), the backend sends a "没听清" notice
      //   so the user knows their message wasn't understood (instead of
      //   staring at "语音消息（4秒）" forever).
      // Don't replace user-typed text — only replace placeholder content.
      // Placeholders: "语音消息（X秒）" / "[语音消息（X秒）]" /
      //               "[系统：没听清...]" / "[系统：语音识别出错...]"
      const isPlaceholder = content =>
        !content ||
        content.startsWith('[语音消息') ||
        content.startsWith('语音消息（') ||
        content.startsWith('[系统：')
      if (targetId && asrText && asrText !== '[语音消息]') {
        setMessages_(prev => prev.map(m => {
          if (m.id !== targetId) {
            return m
          }
          // Only overwrite if the current content is still a placeholder
          // (don't clobber a transcript the user has since edited).
          if (!isPlaceholder(m.content)) {
            console.log('[ACK] skip msg (not placeholder):', m.content.slice(0, 30))
            return m
          }
          console.log('[ACK] updating bubble', m.id, '→', asrText.slice(0, 30))
          return { ...m, content: asrText }
        }))
      }
      return
    }

    if (wsMessage.type === 'ai_streaming_start') {
      // AI response starting - create new message with empty audioData
      const contentPrefix = wsMessage.content || wsMessage.data?.content_prefix as string || ''
      const newMsgId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      currentAIMessageIdRef.current = newMsgId
      const newMessage: MessageItem = {
        id: newMsgId,
        type: 'ai',
        content: contentPrefix,
        audioData: '', // Start with empty audio
        timestamp: wsMessage.timestamp || new Date().toISOString()
      }
      setMessages_(prev => [...prev, newMessage])
      return
    }

    if (wsMessage.type === 'ai_message' || wsMessage.type === 'ai_streaming_end') {
      // Final AI message with audio from backend
      const content = wsMessage.content || wsMessage.data?.content as string || ''
      const audioData = wsMessage.audio_data || ''
      // Backend can attach a freshly-generated persona on the first ai_message
      const persona = (wsMessage as any).persona
      if (persona && persona.name) {
        updatePersona(persona)
      }
      if (content) {
        const newMsgId = wsMessage.id || `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        currentAIMessageIdRef.current = newMsgId
        // Pull knowledge_refs from the message (RAG context) so the chat UI
        // can show "参考资料 (N)" footer under the AI bubble.
        const knowledgeRefs = Array.isArray(wsMessage.knowledge_refs) ? wsMessage.knowledge_refs : []
        // Upsert: if a message with this id already exists (e.g. placeholder → LLM text),
        // update it; otherwise append.
        setMessages_(prev => {
          const existingIdx = prev.findIndex(m => m.id === newMsgId)
          if (existingIdx >= 0) {
            const updated = [...prev]
            updated[existingIdx] = {
              ...updated[existingIdx],
              content,
              audioData: audioData || updated[existingIdx].audioData,
              knowledgeRefs: knowledgeRefs.length > 0 ? knowledgeRefs : updated[existingIdx].knowledgeRefs,
              timestamp: wsMessage.timestamp || updated[existingIdx].timestamp
            }
            return updated
          }
          return [...prev, {
            id: newMsgId,
            type: 'ai' as const,
            content,
            audioData,
            knowledgeRefs: knowledgeRefs.length > 0 ? knowledgeRefs : undefined,
            timestamp: wsMessage.timestamp || new Date().toISOString()
          }]
        })

        // Play audio if available (only on first appearance, not on upsert)
        if (audioData && audioData.length > 0) {
          audioStream.playStoredAudio(audioData)
        }
      }
      return
    }

    // Audio update for an existing message (e.g. first message after TTS finishes)
    if (wsMessage.type === 'ai_message_audio') {
      const targetId = wsMessage.id
      const audioData = wsMessage.audio_data || ''
      if (targetId && audioData) {
        setMessages_(prev => prev.map(m =>
          m.id === targetId ? { ...m, audioData } : m
        ))
        // Play it once
        audioStream.playStoredAudio(audioData)
      }
      return
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

    // phase_complete 消息不再处理：硬性阶段切换已废弃
    // （A1 改动：让对话按真实节奏走，AI 客户按自己判断回应）

    // Handle backchannel (listening acknowledgment)
    if (wsMessage.type === 'backchannel') {
      console.log('[Backchannel]', wsMessage.content)
    }
  }, [updateSessionPhase, updatePersona])

  const handleConnected = useCallback(() => {
    console.log('WebSocket connected')
  }, [])

  const handleDisconnected = useCallback(() => {
    console.log('WebSocket disconnected')
  }, [])

  const { isConnected, sendMessage: wsSendMessage, sendStopPlayback, sendVoiceStart, sendVoiceEnd, sendAudioChunk } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    onAudioChunk: (chunk) => {
      // Play audio immediately when received
      audioStream.playChunk(chunk)
    },
    onConnected: handleConnected,
    onDisconnected: handleDisconnected
  })

  const handleSendMessage = useCallback((content: string, audioData?: string) => {
    // Add user message to local state
    const userMsg: MessageItem = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'user',
      content,
      audioData: audioData || undefined,
      isSending: true,
      timestamp: new Date().toISOString()
    }
    setMessages_(prev => [...prev, userMsg])

    setIsSending(true)

    // Send via WebSocket (include id so the ASR ack can be matched back)
    wsSendMessage(content, audioData, userMsg.id, 'audio/webm')

    // Update message status to show sending
    setMessages_(prev => prev.map(m =>
      m.id === userMsg.id ? { ...m, isSending: false } : m
    ))
    setIsSending(false)
  }, [wsSendMessage])

  // OR-1: Handle stop playback (interrupt AI speech and notify server)
  const handleStopPlayback = useCallback(() => {
    audioStream.stop()
    sendStopPlayback()  // Notify server to stop TTS
  }, [audioStream, sendStopPlayback])

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

        {/* AI Customer Persona - shows concrete character (persona) when available */}
        {currentSession?.persona ? (
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-lg max-w-md">
            <div className="w-10 h-10 bg-secondary/10 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div className="text-sm min-w-0 flex-1">
              <p className="font-medium text-gray-900 truncate">
                {currentSession.persona.name} · {currentSession.persona.title}
              </p>
              <p className="text-gray-500 truncate">
                {currentSession.persona.company}
                {currentSession.persona.industry && ` · ${currentSession.persona.industry}`}
              </p>
            </div>
          </div>
        ) : selectedRoleConfig ? (
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-lg">
            <div className="w-10 h-10 bg-secondary/10 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div className="text-sm">
              <p className="font-medium text-gray-900">
                正在生成客户档案...
              </p>
              <p className="text-gray-500">
                {getRoleLabel(selectedRoleConfig, 'position_level')} · {getRoleLabel(selectedRoleConfig, 'personality')}
              </p>
            </div>
          </div>
        ) : null}
      </header>

      {/* 自由对话指示条（替代旧的硬性 5 阶段 SPIN 进度条） */}
      <div className="bg-white border-b border-gray-200 px-4 py-2">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-700 rounded">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
            自由对话中
          </span>
          {currentSession?.persona?.name && (
            <span className="text-gray-500">
              · 正在和【{currentSession.persona.name}】聊天
            </span>
          )}
          {/* 销售员自填的练习档案徽章 */}
          {userContext && (
            <span className="text-gray-500 truncate">
              {userContext.practice_goals?.length > 0 &&
                `· 重点练: ${userContext.practice_goals.join('/')}`}
              {userContext.difficulty && ` · 难度: ${userContext.difficulty}`}
            </span>
          )}
        </div>
      </div>

      {/* Chat Area with SPIN Stage Hint */}
      <div className="flex-1 overflow-hidden flex">
        <div className="flex-1">
          <ChatContainer
            messages={messages_}
            customerLabel={
              currentSession?.persona
                ? `${currentSession.persona.name}${currentSession.persona.title ? '·' + currentSession.persona.title.split('经理')[0].split('总监')[0] : ''}`
                : 'AI客户'
            }
            onSendMessage={handleSendMessage}
            onVoiceStart={sendVoiceStart}
            onVoiceEnd={sendVoiceEnd}
            onAudioChunk={sendAudioChunk}
            onStopPlayback={handleStopPlayback}
            onPlayAudio={audioStream.playStoredAudio}
            isDisabled={currentSession?.status === 'completed'}
            isSending={isSending}
            isConnected={isConnected}
            isPlayingAudio={audioStream.isPlaying}
          />
        </div>
        {/* OR-4: Real-time SPIN Stage Hint Sidebar */}
        <div className="w-72 border-l border-gray-200 bg-gray-50 overflow-y-auto p-3">
          <p className="text-xs font-medium text-gray-500 mb-3">实时SPIN指导</p>
          <SpinStageHint phase={currentSession?.current_phase || 'opening'} />
        </div>
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

export default PracticeChatPage
