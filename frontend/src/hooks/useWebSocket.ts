/**
 * useWebSocket Hook - Enhanced for streaming voice conversation
 * Supports binary audio chunks, state sync, and backchannel
 */
import { useEffect, useRef, useState, useCallback } from 'react'

export type ConversationState = 'idle' | 'user_speaking' | 'ai_speaking' | 'processing'

export interface StreamMessage {
  type: 'user_message' | 'ai_message' | 'ai_streaming_start' | 'ai_streaming_update' |
        'ai_streaming_end' | 'audio_chunk' | 'backchannel' | 'status_update' |
        'stop_playback' | 'playback_stopped' | 'summary_trigger' | 'phase_complete' | 'system'
  content?: string
  audio_data?: string
  state?: ConversationState
  timestamp: string
  data?: Record<string, unknown>
}

interface UseWebSocketOptions {
  url: string | null
  onMessage?: (message: StreamMessage) => void
  onAudioChunk?: (chunk: Uint8Array) => void
  onStateChange?: (state: ConversationState) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: Event) => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  isConnecting: boolean
  sendMessage: (message: string, audioData?: string) => void
  sendAudioChunk: (chunk: Uint8Array) => void
  sendStopPlayback: () => void
  sendVoiceStart: () => void
  sendVoiceEnd: () => void
  disconnect: () => void
  lastMessage: StreamMessage | null
  lastAudioChunk: Uint8Array | null
  state: ConversationState
}

export const useWebSocket = ({
  url,
  onMessage,
  onAudioChunk,
  onStateChange,
  onConnected,
  onDisconnected,
  onError
}: UseWebSocketOptions): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [lastMessage, setLastMessage] = useState<StreamMessage | null>(null)
  const [lastAudioChunk, setLastAudioChunk] = useState<Uint8Array | null>(null)
  const [state, setState] = useState<ConversationState>('idle')

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!url) return

    setIsConnecting(true)

    try {
      const ws = new WebSocket(url)
      ws.binaryType = 'arraybuffer'  // Important for audio chunks

      ws.onopen = () => {
        setIsConnected(true)
        setIsConnecting(false)
        onConnected?.()
      }

      ws.onmessage = (event) => {
        // Handle binary audio chunks
        if (event.data instanceof ArrayBuffer) {
          const chunk = new Uint8Array(event.data)
          setLastAudioChunk(chunk)
          onAudioChunk?.(chunk)
          return
        }

        // Handle JSON messages
        try {
          const message: StreamMessage = JSON.parse(event.data)
          setLastMessage(message)

          if (message.type === 'status_update' && message.state) {
            setState(message.state)
            onStateChange?.(message.state)
          }

          onMessage?.(message)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }

      ws.onclose = () => {
        setIsConnected(false)
        setIsConnecting(false)
        onDisconnected?.()
      }

      wsRef.current = ws
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      setIsConnecting(false)
    }
  }, [url, onMessage, onAudioChunk, onStateChange, onConnected, onDisconnected, onError])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((message: string, audioData?: string) => {
    console.log('[WS] sendMessage called, readyState:', wsRef.current?.readyState)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify({
        type: 'user_message',
        content: message,
        audio_data: audioData,
        timestamp: new Date().toISOString()
      })
      console.log('[WS] Sending message:', payload)
      wsRef.current.send(payload)
    } else {
      console.log('[WS] WebSocket not open, readyState:', wsRef.current?.readyState)
    }
  }, [])

  const sendAudioChunk = useCallback((chunk: Uint8Array) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk)
    }
  }, [])

  const sendStopPlayback = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_playback' }))
    }
  }, [])

  const sendVoiceStart = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'voice_start' }))
    }
  }, [])

  const sendVoiceEnd = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'voice_end' }))
    }
  }, [])

  useEffect(() => {
    if (url) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [url, connect, disconnect])

  return {
    isConnected,
    isConnecting,
    sendMessage,
    sendAudioChunk,
    sendStopPlayback,
    sendVoiceStart,
    sendVoiceEnd,
    disconnect,
    lastMessage,
    lastAudioChunk,
    state
  }
}

export default useWebSocket