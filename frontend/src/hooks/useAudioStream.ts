/**
 * useAudioStream - Streaming audio playback hook
 * Handles chunked audio playback with interruption support
 */
import { useState, useRef, useCallback } from 'react'

interface UseAudioStreamReturn {
  isPlaying: boolean
  isBuffering: boolean
  currentPosition: number
  duration: number
  playChunk: (chunk: Uint8Array) => void
  playBase64Chunk: (base64: string) => void
  stop: () => void
  pause: () => void
  resume: () => void
}

export function useAudioStream(): UseAudioStreamReturn {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isBuffering, setIsBuffering] = useState(false)
  const [currentPosition, setCurrentPosition] = useState(0)
  const [duration, setDuration] = useState(0)

  const audioContextRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<AudioBufferSourceNode | null>(null)
  const audioBufferRef = useRef<AudioBuffer | null>(null)
  const chunkQueueRef = useRef<Uint8Array[]>([])
  const isPlayingRef = useRef(false)
  const isInterruptedRef = useRef(false)
  const startTimeRef = useRef(0)
  const pausedAtRef = useRef(0)

  const processQueue = useCallback(async () => {
    if (!audioContextRef.current || chunkQueueRef.current.length === 0) return

    isInterruptedRef.current = false

    // Combine all queued chunks
    const totalLength = chunkQueueRef.current.reduce((sum, chunk) => sum + chunk.length, 0)
    const combinedBuffer = new Uint8Array(totalLength)
    let offset = 0
    for (const chunk of chunkQueueRef.current) {
      combinedBuffer.set(chunk, offset)
      offset += chunk.length
    }
    chunkQueueRef.current = []

    setIsBuffering(true)

    try {
      // Decode MP3 data
      const audioBuffer = await audioContextRef.current.decodeAudioData(
        combinedBuffer.buffer.slice(0)
      )
      audioBufferRef.current = audioBuffer

      // Play the audio
      const source = audioContextRef.current.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContextRef.current.destination)

      source.onended = () => {
        if (!isInterruptedRef.current) {
          setIsPlaying(false)
          setCurrentPosition(0)
          setIsBuffering(false)
        }
      }

      sourceRef.current = source
      isPlayingRef.current = true

      const offsetTime = pausedAtRef.current || 0
      startTimeRef.current = audioContextRef.current.currentTime - offsetTime

      source.start(0, offsetTime)
      setIsPlaying(true)
      setIsBuffering(false)
      setDuration(audioBuffer.duration)

      // Update position
      const updatePosition = () => {
        if (isPlayingRef.current && audioContextRef.current) {
          const elapsed = audioContextRef.current.currentTime - startTimeRef.current
          setCurrentPosition(Math.min(elapsed, audioBuffer.duration))
          if (elapsed < audioBuffer.duration) {
            requestAnimationFrame(updatePosition)
          }
        }
      }
      updatePosition()

    } catch (error) {
      console.error('Failed to decode audio:', error)
      setIsBuffering(false)
    }
  }, [])

  const playChunk = useCallback((chunk: Uint8Array) => {
    // Initialize AudioContext if needed (must be from user gesture)
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext()
    }

    // Resume context if suspended
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume()
    }

    chunkQueueRef.current.push(chunk)

    if (!isPlayingRef.current) {
      processQueue()
    }
  }, [processQueue])

  const playBase64Chunk = useCallback((base64: string) => {
    const binaryString = atob(base64)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    playChunk(bytes)
  }, [playChunk])

  const stop = useCallback(() => {
    isInterruptedRef.current = true

    if (sourceRef.current) {
      try {
        sourceRef.current.stop()
      } catch {
        // Already stopped
      }
      sourceRef.current = null
    }

    isPlayingRef.current = false
    pausedAtRef.current = 0
    chunkQueueRef.current = []

    setIsPlaying(false)
    setCurrentPosition(0)
    setIsBuffering(false)
  }, [])

  const pause = useCallback(() => {
    if (isPlayingRef.current && audioContextRef.current) {
      pausedAtRef.current = audioContextRef.current.currentTime - startTimeRef.current
      stop()
    }
  }, [stop])

  const resume = useCallback(() => {
    if (audioBufferRef.current && !isPlayingRef.current) {
      isInterruptedRef.current = false

      const source = audioContextRef.current!.createBufferSource()
      source.buffer = audioBufferRef.current
      source.connect(audioContextRef.current!.destination)

      source.onended = () => {
        if (!isInterruptedRef.current) {
          setIsPlaying(false)
        }
      }

      sourceRef.current = source
      isPlayingRef.current = true
      startTimeRef.current = audioContextRef.current!.currentTime - pausedAtRef.current
      source.start(0, pausedAtRef.current)
      setIsPlaying(true)

      pausedAtRef.current = 0
    }
  }, [])

  return {
    isPlaying,
    isBuffering,
    currentPosition,
    duration,
    playChunk,
    playBase64Chunk,
    stop,
    pause,
    resume
  }
}