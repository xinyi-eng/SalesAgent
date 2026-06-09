/**
 * ChatContainer Component - Main chat interface
 * Enhanced with streaming audio support, VAD events, and playback control.
 *
 * NOTE: this component used to instantiate its own `useAudioStream()`,
 * which made playback state desync from the parent's audioStream
 * (clicking "播放" actually played audio, but the play indicator never
 * updated because it was reading the wrong instance). The container now
 * only consumes the audioStream via props from the parent.
 */
import { useEffect, useRef, useState } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'

interface KnowledgeRef {
  category?: string
  source?: string
  chapter?: string
  section?: string
  excerpt?: string
  relevance?: number
}

interface MessageItem {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  audioData?: string  // Base64 encoded audio
  isSending?: boolean
  timestamp: string
  knowledgeRefs?: KnowledgeRef[]
}

interface ChatContainerProps {
  messages: MessageItem[]
  customerLabel?: string
  onSendMessage: (message: string, audioData?: string) => void
  onVoiceStart?: () => void
  onVoiceEnd?: () => void
  onStopPlayback?: () => void
  onPlayAudio?: (audioData: string) => void
  isDisabled?: boolean
  isSending?: boolean
  isConnected?: boolean
  isPlayingAudio?: boolean
}

const ChatContainer = ({
  messages,
  customerLabel,
  onSendMessage,
  onVoiceStart,
  onVoiceEnd,
  onStopPlayback,
  onPlayAudio,
  isDisabled = false,
  isSending = false,
  isConnected = false,
  isPlayingAudio = false
}: ChatContainerProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isNearBottom, setIsNearBottom] = useState(true)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isNearBottom) {
      scrollToBottom()
    }
  }, [messages])

  const handleScroll = () => {
    const container = containerRef.current
    if (container) {
      const threshold = 100
      const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold
      setIsNearBottom(isAtBottom)
    }
  }

  // Play audio message - delegate to parent (which owns the audioStream)
  const handlePlayAudio = (audioData: string) => {
    if (onPlayAudio) {
      onPlayAudio(audioData)
    } else {
      console.warn('[ChatContainer] No onPlayAudio prop provided; cannot play audio.')
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Connection Status */}
      {!isConnected && !isDisabled && (
        <div className="bg-yellow-50 border-b border-yellow-100 px-4 py-2">
          <p className="text-sm text-yellow-700 text-center">
            正在连接AI服务器...
          </p>
        </div>
      )}

      {/* Messages Area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-gray-500 text-sm">开始与AI客户对话</p>
              <p className="text-gray-400 text-xs mt-1">按住麦克风说话，或输入文字</p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            type={message.type}
            content={message.content}
            audioData={message.audioData}
            isSending={message.isSending}
            timestamp={message.timestamp}
            onPlayAudio={message.audioData ? () => handlePlayAudio(message.audioData!) : undefined}
            isPlayingAudio={isPlayingAudio}
            customerLabel={customerLabel}
            knowledgeRefs={message.knowledgeRefs}
          />
        ))}

        {/* Typing Indicator */}
        {isSending && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-2xl bg-white border border-gray-200 rounded-bl-md">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {/* Streaming indicator */}
        {isPlayingAudio && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-2xl bg-primary/10 text-primary text-sm">
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                AI 正在说话...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Jump to Bottom Button */}
      {!isNearBottom && messages.length > 0 && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-20 left-1/2 -translate-x-1/2 px-4 py-2 bg-primary text-white rounded-full shadow-lg text-sm"
        >
          最新消息
        </button>
      )}

      {/* Input Area */}
      <ChatInput
        onSendMessage={onSendMessage}
        onVoiceStart={onVoiceStart}
        onVoiceEnd={onVoiceEnd}
        onStopPlayback={onStopPlayback}
        isDisabled={isDisabled}
        isSending={isSending}
        isPlayingAudio={isPlayingAudio}
      />
    </div>
  )
}

export default ChatContainer