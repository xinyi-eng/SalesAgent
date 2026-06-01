/**
 * ChatInput Component - Message input for chat with voice recording
 * Enhanced with VAD state visualization and stop playback button
 */
import { useState, useRef, KeyboardEvent } from 'react'
import { useAudioRecorder } from '../../../hooks/useAudioRecorder'

interface ChatInputProps {
  onSendMessage: (message: string, audioData?: string) => void
  onVoiceStart?: () => void
  onVoiceEnd?: () => void
  onStopPlayback?: () => void
  isDisabled?: boolean
  isSending?: boolean
  isPlayingAudio?: boolean
}

const ChatInput = ({
  onSendMessage,
  onVoiceStart,
  onVoiceEnd,
  onStopPlayback,
  isDisabled = false,
  isSending = false,
  isPlayingAudio = false
}: ChatInputProps) => {
  const [message, setMessage] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const {
    isRecording: recorderIsRecording,
    isPlaying,
    isVoiceDetected,
    startRecording,
    stopRecording,
    playAudio,
    audioLevel
  } = useAudioRecorder()

  const handleSend = () => {
    if (!message.trim() || isDisabled || isSending) return
    onSendMessage(message.trim())
    setMessage('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value)
    // Auto-resize textarea
    const textarea = inputRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }

  const handleStartRecording = async () => {
    if (isDisabled) return
    try {
      await startRecording()
      setIsRecording(true)
      onVoiceStart?.()
    } catch (error) {
      console.error('Failed to start recording:', error)
      alert('无法访问麦克风，请检查权限设置')
    }
  }

  const handleStopRecording = async () => {
    if (!isRecording) return
    try {
      const base64Audio = await stopRecording()
      setIsRecording(false)
      onVoiceEnd?.()
      onSendMessage('[语音消息]', base64Audio)
    } catch (error) {
      console.error('Failed to stop recording:', error)
      setIsRecording(false)
    }
  }

  const handlePlayAudio = (audioData: string) => {
    playAudio(audioData)
  }

  const canSend = message.trim() && !isDisabled && !isSending

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="flex items-end gap-3">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={isDisabled ? '对练已结束' : '输入消息或按住麦克风说话...'}
            disabled={isDisabled || isSending}
            rows={1}
            className={`
              w-full resize-none rounded-xl border-2 px-4 py-3 pr-20
              focus:outline-none focus:ring-2 focus:ring-primary/20
              transition-all duration-200
              ${isDisabled
                ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
                : 'border-gray-200 focus:border-primary'
              }
              ${isSending ? 'opacity-70' : ''}
              ${isRecording ? 'border-red-300 bg-red-50' : ''}
            `}
          />

          {/* Recording indicator with VAD state */}
          {isRecording && (
            <div className="absolute right-16 bottom-2 flex items-center gap-2">
              <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${
                isVoiceDetected ? 'bg-green-100' : 'bg-red-100'
              }`}>
                <div className={`w-2 h-2 rounded-full animate-pulse ${
                  isVoiceDetected ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <span className={`text-xs font-medium ${
                  isVoiceDetected ? 'text-green-600' : 'text-red-600'
                }`}>
                  {isVoiceDetected ? '检测到语音' : '等待语音...'}
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {Math.round(audioLevel * 100)}%
              </span>
            </div>
          )}

          {/* Stop playback button when AI is speaking */}
          {isPlayingAudio && (
            <div className="absolute right-16 bottom-2">
              <button
                onClick={onStopPlayback}
                className="flex items-center gap-1 px-2 py-1 bg-red-100 text-red-600 rounded-full text-xs hover:bg-red-200"
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" />
                </svg>
                停止播放
              </button>
            </div>
          )}

          {/* Action buttons */}
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            {/* Voice record button */}
            <button
              onMouseDown={handleStartRecording}
              onMouseUp={handleStopRecording}
              onMouseLeave={() => isRecording && handleStopRecording()}
              disabled={isDisabled || isSending}
              className={`
                w-8 h-8 rounded-lg flex items-center justify-center
                transition-all duration-200
                ${isRecording
                  ? 'bg-red-500 text-white animate-pulse'
                  : isDisabled
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
              title="按住说话"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>

            {/* Text send button */}
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`
                w-8 h-8 rounded-lg flex items-center justify-center
                transition-all duration-200
                ${canSend
                  ? 'bg-primary text-white hover:bg-primary/90'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }
              `}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-2 text-center">
        按 Enter 发送，Shift + Enter 换行 | 按住麦克风说话
      </p>
    </div>
  )
}

export default ChatInput