/**
 * ChatMessage Component
 *
 * Displays a single chat message with role indicator
 * Supports: user message, AI message, system message
 * Also supports audio playback for AI responses
 */
import { WebSocketMessage } from '../../../hooks/useWebSocket'

interface ChatMessageProps {
  type: 'user' | 'ai' | 'system'
  content: string
  audioData?: string
  isSending?: boolean
  timestamp: string
  onPlayAudio?: () => void
  isPlayingAudio?: boolean
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
  isPlayingAudio
}: ChatMessageProps) => {
  const styles = roleStyles[type] || roleStyles.system
  const label = roleLabels[type] || '系统'

  const formatTime = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={`flex ${styles.container}`}>
      <div className={`max-w-[75%] ${type === 'user' ? 'order-2' : 'order-1'}`}>
        {/* Label */}
        <div className={`text-xs font-medium mb-1 ${styles.label}`}>
          {label}
        </div>

        {/* Bubble */}
        <div className={`px-4 py-2 ${styles.bubble} ${isSending ? 'opacity-70' : ''}`}>
          <p className="whitespace-pre-wrap">{content}</p>

          {/* Audio playback button */}
          {audioData && type === 'ai' && (
            <button
              onClick={onPlayAudio}
              disabled={isPlayingAudio}
              className={`
                mt-2 flex items-center gap-2 px-3 py-1.5 rounded-full
                transition-all text-sm
                ${isPlayingAudio
                  ? 'bg-secondary/20 text-secondary'
                  : 'bg-white/50 hover:bg-white/80 text-gray-600'
                }
              `}
            >
              {isPlayingAudio ? (
                <>
                  <div className="w-3 h-3 border-2 border-secondary/30 border-t-secondary rounded-full animate-spin" />
                  播放中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15.414a5 5 0 001.414 1.414m2.828-9.9a9 9 0 012.828 2.828" />
                  </svg>
                  播放语音
                </>
              )}
            </button>
          )}
        </div>

        {/* Time */}
        <div className={`text-xs text-gray-400 mt-1 ${type === 'user' ? 'text-right' : 'text-left'}`}>
          {formatTime(timestamp)}
        </div>
      </div>
    </div>
  )
}

export default ChatMessage