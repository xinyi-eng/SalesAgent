/**
 * useWebSocket Hook - Enhanced for streaming voice conversation
 * Supports binary audio chunks, state sync, and backchannel
 */
import { useEffect, useRef, useState, useCallback } from 'react'

export type ConversationState = 'idle' | 'user_speaking' | 'ai_speaking' | 'processing'

export interface StreamMessage {
  type: 'user_message' | 'user_message_ack' | 'ai_message' | 'ai_message_audio' | 'ai_streaming_start' | 'ai_streaming_update' |
        'ai_streaming_end' | 'audio_chunk' | 'backchannel' | 'status_update' |
        'stop_playback' | 'playback_stopped' | 'summary_trigger' | 'phase_complete' | 'system'
  id?: string
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
  sendMessage: (message: string, audioData?: string, id?: string, audioMime?: string) => void
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
  const connectingRef = useRef(false)

  const connect = useCallback(() => {
    if (!url) return

    // Guard: don't connect if already connecting or connected
    if (connectingRef.current) {
      console.log('[WS] Already connecting, skip')
      return
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected')
      return
    }
    // Clean up dead socket
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CONNECTING) {
      wsRef.current = null
    }

    console.log('[WS] Connecting to:', url)
    connectingRef.current = true
    setIsConnecting(true)

    const ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      console.log('[WS] Connected!')
      connectingRef.current = false
      setIsConnected(true)
      setIsConnecting(false)
      onConnected?.()
    }

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        const chunk = new Uint8Array(event.data)
        console.log('[WS] Binary received:', chunk.length, 'bytes')
        setLastAudioChunk(chunk)
        onAudioChunk?.(chunk)
        return
      }
      try {
        const message: StreamMessage = JSON.parse(event.data)
        setLastMessage(message)
        if (message.type === 'status_update' && message.state) {
          setState(message.state)
          onStateChange?.(message.state)
        }
        onMessage?.(message)
      } catch (e) {
        console.error('[WS] Parse error:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('[WS] Error:', error)
      onError?.(error)
    }

    ws.onclose = (event) => {
      console.log('[WS] Closed. code:', event.code, 'reason:', event.reason, 'wasClean:', event.wasClean)
      console.trace('[WS] close stack')
      connectingRef.current = false
      setIsConnected(false)
      setIsConnecting(false)
      wsRef.current = null
      onDisconnected?.()
    }

    wsRef.current = ws
  }, [url, onMessage, onAudioChunk, onStateChange, onConnected, onDisconnected, onError])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    connectingRef.current = false
  }, [])

  const sendMessage = useCallback((message: string, audioData?: string, id?: string, audioMime?: string) => {
    const ws = wsRef.current
    if (!ws) {
      console.warn('[WS] sendMessage: no ws ref')
      return
    }
    console.log('[WS] sendMessage readyState=', ws.readyState, 'OPEN=', WebSocket.OPEN)
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'user_message',
        id,
        content: message,
        audio_data: audioData,
        audio_mime: audioMime,
        timestamp: new Date().toISOString()
      }))
      console.log('[WS] sent user_message:', message.slice(0, 30))
    } else {
      console.warn('[WS] sendMessage: ws not open, dropping message')
    }
  }, [])

  const sendAudioChunk = useCallback((chunk: Uint8Array) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk)
    }
  }, [])

  const sendStopPlayback = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_playback' }))
    }
  }, [])

  const sendVoiceStart = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'voice_start' }))
    }
  }, [])

  const sendVoiceEnd = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'voice_end' }))
    }
  }, [])

  useEffect(() => {
    if (!url) return
    // Guard: skip if already connecting or connected
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      console.log('[WS] Already connecting/connected, skip')
      return
    }
    console.log('[WS] Initializing connection to:', url)
    connect()
    // Intentionally do NOT disconnect on cleanup - the WS connection
    // should persist across React re-renders / strict-mode double mounts
    // to avoid spurious "close" events from interrupting the backend.
  }, [url])

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