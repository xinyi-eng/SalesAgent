/**
 * ChatMessage Component
 *
 * Displays a single chat message with role indicator
 * Supports: user message, AI message, system message
 * Shows: audio player, text transcript, replay button, timestamp,
 *        and (for AI) the RAG knowledge references the reply cited.
 */
import React from 'react'

interface KnowledgeRef {
  category?: string
  source?: string
  chapter?: string
  section?: string
  excerpt?: string
  relevance?: number
}

interface ChatMessageProps {
  type: 'user' | 'ai' | 'system'
  content: string
  audioData?: string  // base64 encoded audio
  isSending?: boolean
  timestamp: string
  onPlayAudio?: () => void
  isPlayingAudio?: boolean
  // For AI messages: show concrete customer name + title@company
  customerLabel?: string
  // Knowledge base references the AI cited (RAG output)
  knowledgeRefs?: KnowledgeRef[]
}

const roleStyles = {
  user: {
    container: 'justify-end',
    bubble: 'bg-primary text-white rounded-2xl rounded-br-sm',
    label: 'text-primary'
  },
  ai: {
    container: 'justify-start',
    bubble: 'bg-gray-100 text-gray-900 rounded-2xl rounded-bl-sm',
    label: 'text-secondary'
  },
  system: {
    container: 'justify-center',
    bubble: 'bg-gray-50 text-gray-500 text-center text-sm italic',
    label: 'text-gray-400'
  }
}

const roleLabels = {
  user: '我',
  ai: 'AI客户',
  system: '系统'
}

const ChatMessage = ({
  type,
  content,
  audioData,
  isSending,
  timestamp,
  onPlayAudio,
  isPlayingAudio,
  customerLabel,
  knowledgeRefs
}: ChatMessageProps) => {
  const [refsOpen, setRefsOpen] = React.useState(false)
  const styles = roleStyles[type] || roleStyles.system
  // For AI messages, show concrete customer label (e.g. "张总") if provided
  const label = type === 'ai' && customerLabel ? customerLabel : (roleLabels[type] || '系统')

  const formatTime = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  // Strip emotion tags from display content but keep them in audio.
  // Tags come in three shapes:
  //   - English parens: (clears throat), (snorts)
  //   - Chinese parens: （clears throat） — the LLM often writes these
  //   - Hyphenated:     (clear-throat)
  // Also drop MiniMax M-series `<think>...</think>` reasoning leakage.
  const displayContent = content
    .replace(/<think>[\s\S]*?<\/think>/g, '')
    .replace(
      /[（(](laughs|sighs|breath|chuckle|groans|inhale|exhale|gasps|sniffs|humming|hissing|emm|whistles|sneezes|crying|applause|coughs|clears?[- ]throat|pant|burps|lip-smacking|snorts)[)）]/g,
      ''
    )

  return (
    <div className={`flex ${styles.container}`}>
      <div className={`max-w-[80%] ${type === 'user' ? 'order-2' : 'order-1'}`}>
        {/* Label */}
        <div className={`text-xs font-medium mb-1 ${styles.label}`}>
          {label}
        </div>

        {/* Bubble */}
        <div className={`px-4 py-3 ${styles.bubble} ${isSending ? 'opacity-70' : ''}`}>
          {/* Audio Player - for AI messages */}
          {audioData && type === 'ai' && (
            <div className="mb-3 flex items-center gap-2 bg-white/60 rounded-lg p-2">
              {/* Play/Pause button */}
              <button
                onClick={onPlayAudio}
                disabled={isPlayingAudio}
                aria-label={isPlayingAudio ? '停止播放' : '点击播放'}
                className={`
                  flex items-center justify-center w-9 h-9 rounded-full
                  transition-all flex-shrink-0 shadow-sm
                  ${isPlayingAudio
                    ? 'bg-secondary text-white'
                    : 'bg-primary text-white hover:bg-primary/90'
                  }
                `}
              >
                {isPlayingAudio ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="6" y="4" width="4" height="16" />
                    <rect x="14" y="4" width="4" height="16" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                )}
              </button>

              {/* Audio waveform indicator */}
              <div className="flex-1 flex items-center gap-0.5 min-w-0">
                {[...Array(16)].map((_, i) => (
                  <div
                    key={i}
                    className={`
                      w-1 rounded-full transition-all flex-shrink-0
                      ${isPlayingAudio ? 'bg-secondary animate-pulse' : 'bg-gray-400/60'}
                    `}
                    style={{
                      height: `${Math.random() * 18 + 6}px`,
                      animationDelay: `${i * 0.05}s`
                    }}
                  />
                ))}
              </div>

              {/* Play / Replay label */}
              <button
                onClick={onPlayAudio}
                className="flex items-center gap-1 text-xs text-gray-600 hover:text-primary flex-shrink-0"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {isPlayingAudio ? '播放中' : '重播'}
              </button>
            </div>
          )}

          {/* Text content (transcript) */}
          <p className="whitespace-pre-wrap leading-relaxed">{displayContent || content}</p>

          {/* Audio indicator for user messages (ASR input) */}
          {audioData && type === 'user' && (
            <div className="mt-3 pt-2 border-t border-white/20 flex items-center gap-2">
              <svg className="w-4 h-4 text-white flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <span className="text-sm font-medium text-white flex-1">
                {displayContent && /（\d+秒）/.test(displayContent)
                  ? displayContent
                  : '语音消息'}
              </span>
              <button
                onClick={onPlayAudio}
                className="flex items-center gap-1 text-xs text-white/90 hover:text-white bg-white/15 hover:bg-white/25 rounded-full px-2 py-1"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {isPlayingAudio ? '播放中' : '重播'}
              </button>
            </div>
          )}
        </div>

        {/* Time and status */}
        <div className={`flex items-center gap-2 mt-1 ${type === 'user' ? 'justify-end' : 'justify-start'}`}>
          <span className="text-xs text-gray-400">{formatTime(timestamp)}</span>
          {isSending && (
            <span className="text-xs text-gray-400 animate-pulse">发送中...</span>
          )}
        </div>

        {/* Knowledge references footer (AI messages only) */}
        {type === 'ai' && knowledgeRefs && knowledgeRefs.length > 0 && (
          <div className="mt-1 max-w-md">
            <button
              onClick={() => setRefsOpen(!refsOpen)}
              className="flex items-center gap-1 text-xs text-secondary hover:text-secondary/80 transition-colors"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.186 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <span>AI 参考资料 ({knowledgeRefs.length})</span>
              <svg
                className={`w-3 h-3 transition-transform ${refsOpen ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {refsOpen && (
              <div className="mt-2 space-y-1.5">
                <p className="text-[10px] text-gray-500 leading-relaxed">
                  本次 AI 回复参考的销售方法/话术来源（已融进 AI 客户的自然对话里）：
                </p>
                {knowledgeRefs.map((ref, idx) => (
                  <div
                    key={idx}
                    className="bg-white/60 border border-secondary/20 rounded-md px-2.5 py-1.5 text-xs flex items-center gap-2"
                  >
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-secondary/10 text-secondary text-[9px] font-medium flex-shrink-0">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0 truncate">
                      <span className="font-medium text-gray-700">
                        {ref.source || '知识库'}
                      </span>
                      {ref.chapter && (
                        <span className="text-gray-500"> · {ref.chapter}</span>
                      )}
                    </div>
                    {ref.relevance != null && (
                      <span className="text-[10px] text-gray-400 flex-shrink-0">
                        相关度 {(ref.relevance * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage