/**
 * useAudioStream - Streaming audio playback hook
 * Handles chunked audio playback with interruption support
 * Uses HTML5 Audio element for reliable MP3 playback
 */
import { useState, useRef, useCallback } from 'react'

// Ensure AudioContext is available
declare const AudioContext: typeof undefined | ((options?: any) => any)

interface UseAudioStreamReturn {
  isPlaying: boolean
  isBuffering: boolean
  currentPosition: number
  duration: number
  playChunk: (chunk: Uint8Array) => void
  playBase64Chunk: (base64: string) => void
  playStoredAudio: (base64Audio: string) => void
  stop: () => void
  pause: () => void
  resume: () => void
  currentAudioUrl: string | null
}

export function useAudioStream(): UseAudioStreamReturn {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isBuffering, setIsBuffering] = useState(false)
  const [currentPosition, setCurrentPosition] = useState(0)
  const [duration, setDuration] = useState(0)

  const audioElementRef = useRef<HTMLAudioElement | null>(null)
  const chunkQueueRef = useRef<Uint8Array[]>([])
  const isPlayingRef = useRef(false)
  const isInterruptedRef = useRef(false)
  const currentUrlRef = useRef<string | null>(null)

  const processQueue = useCallback(() => {
    console.log('[AudioStream] processQueue called, queue length:', chunkQueueRef.current.length)
    if (chunkQueueRef.current.length === 0) {
      console.log('[AudioStream] Queue empty, returning')
      return
    }

    isInterruptedRef.current = false
    setIsBuffering(true)

    // Combine all queued chunks
    const totalLength = chunkQueueRef.current.reduce((sum, chunk) => sum + chunk.length, 0)
    console.log('[AudioStream] Combining', chunkQueueRef.current.length, 'chunks, total size:', totalLength)
    const combinedBuffer = new Uint8Array(totalLength)
    let offset = 0
    for (const chunk of chunkQueueRef.current) {
      combinedBuffer.set(chunk, offset)
      offset += chunk.length
    }
    chunkQueueRef.current = []

    // Clean up previous audio
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current.src = ''
    }
    if (currentUrlRef.current) {
      URL.revokeObjectURL(currentUrlRef.current)
      currentUrlRef.current = null
    }

    // MiniMax TTS returns standard MP3 format (OpenAI-compatible API)
    // Use HTML5 Audio with blob URL for reliable MP3 playback
    const blob = new Blob([combinedBuffer], { type: 'audio/mpeg' })
    const url = URL.createObjectURL(blob)
    currentUrlRef.current = url
    console.log('[AudioStream] Created MP3 blob URL')

    const audio = new Audio(url)
    audioElementRef.current = audio

    audio.onloadedmetadata = () => {
      console.log('[AudioStream] Metadata loaded, duration:', audio.duration)
      setDuration(audio.duration)
      setIsBuffering(false)
    }

    audio.onplay = () => {
      console.log('[AudioStream] Playing MP3!')
      setIsPlaying(true)
      isPlayingRef.current = true
      setIsBuffering(false)
    }

    audio.onended = () => {
      console.log('[AudioStream] Ended')
      if (!isInterruptedRef.current) {
        setIsPlaying(false)
        setCurrentPosition(0)
        isPlayingRef.current = false
      }
    }

    audio.onerror = (e) => {
      console.error('[AudioStream] MP3 Audio error:', audio.error)
      setIsPlaying(false)
      setIsBuffering(false)
      isPlayingRef.current = false
    }

    audio.ontimeupdate = () => {
      setCurrentPosition(audio.currentTime)
    }

    audio.preload = 'auto'
    console.log('[AudioStream] Calling audio.play()')
    audio.play().catch(err => {
      console.error('[AudioStream] Play error:', err)
      setIsPlaying(false)
      setIsBuffering(false)
      isPlayingRef.current = false
    })
  }, [])

  const playChunk = useCallback((chunk: Uint8Array) => {
    console.log('[AudioStream] playChunk called, queue size:', chunkQueueRef.current.length, 'chunk size:', chunk.length)
    chunkQueueRef.current.push(chunk)

    console.log('[AudioStream] isPlayingRef:', isPlayingRef.current)
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

  // Play stored/replayed audio from base64
  const playStoredAudio = useCallback((base64Audio: string) => {
    console.log('[AudioStream] playStoredAudio called, length:', base64Audio.length)

    // Stop current playback
    isInterruptedRef.current = true
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current.src = ''
    }

    try {
      // Decode base64
      const binaryString = atob(base64Audio)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      console.log('[AudioStream] Decoded bytes:', bytes.length)

      // Sniff mime from magic bytes so user-recorded webm/opus and AI mp3 both work
      let mime = 'audio/mpeg'
      if (bytes.length >= 4) {
        // "ID3" (mp3 with ID3 tag) or 0xFF 0xFB/0xFA/0xF3/0xF2 (mp3 frame sync) -> mp3
        if (bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33) {
          mime = 'audio/mpeg'
        } else if (bytes[0] === 0xFF && (bytes[1] & 0xE0) === 0xE0) {
          mime = 'audio/mpeg'
        } else if (bytes[0] === 0x1A && bytes[1] === 0x45 && bytes[2] === 0xDF) {
          // EBML header (webm/matroska)
          mime = 'audio/webm'
        } else if (bytes[0] === 0x4F && bytes[1] === 0x67 && bytes[2] === 0x67 && bytes[3] === 0x53) {
          // OGG container
          mime = 'audio/ogg'
        } else if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46) {
          // RIFF (wav)
          mime = 'audio/wav'
        } else if (bytes[0] === 0x66 && bytes[1] === 0x4C && bytes[2] === 0x61 && bytes[3] === 0x43) {
          // FLAC
          mime = 'audio/flac'
        } else if (bytes[0] === 0xFF && bytes[1] === 0xF1) {
          // AAC ADTS
          mime = 'audio/aac'
        }
      }
      console.log('[AudioStream] Detected mime:', mime)

      // Clean up previous URL
      if (currentUrlRef.current) {
        URL.revokeObjectURL(currentUrlRef.current)
        currentUrlRef.current = null
      }

      // Create blob and play
      const blob = new Blob([bytes], { type: mime })
      const url = URL.createObjectURL(blob)
      currentUrlRef.current = url

      const audio = new Audio(url)
      audioElementRef.current = audio

      audio.onloadedmetadata = () => {
        console.log('[AudioStream] Replay metadata loaded, duration:', audio.duration)
        setDuration(audio.duration)
      }

      audio.onplay = () => {
        console.log('[AudioStream] Replay playing!')
        setIsPlaying(true)
        isPlayingRef.current = true
        setIsBuffering(false)
      }

      audio.onended = () => {
        console.log('[AudioStream] Replay ended')
        setIsPlaying(false)
        setCurrentPosition(0)
        isPlayingRef.current = false
      }

      audio.onerror = (e) => {
        console.error('[AudioStream] Replay error:', audio.error, 'mime:', mime)
        setIsPlaying(false)
        setIsBuffering(false)
        isPlayingRef.current = false
      }

      audio.ontimeupdate = () => {
        setCurrentPosition(audio.currentTime)
      }

      audio.preload = 'auto'
      audio.play().catch(err => {
        console.error('[AudioStream] Replay play error:', err)
        setIsPlaying(false)
        setIsBuffering(false)
        isPlayingRef.current = false
      })
    } catch (e) {
      console.error('[AudioStream] Failed to decode base64:', e)
    }
  }, [])

  const stop = useCallback(() => {
    console.log('[AudioStream] stop called')
    isInterruptedRef.current = true

    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current.currentTime = 0
    }

    isPlayingRef.current = false
    chunkQueueRef.current = []

    setIsPlaying(false)
    setCurrentPosition(0)
    setIsBuffering(false)
  }, [])

  const pause = useCallback(() => {
    if (audioElementRef.current && isPlayingRef.current) {
      audioElementRef.current.pause()
      isPlayingRef.current = false
      setIsPlaying(false)
    }
  }, [])

  const resume = useCallback(() => {
    if (audioElementRef.current && !isPlayingRef.current) {
      audioElementRef.current.play()
      isPlayingRef.current = true
      setIsPlaying(true)
    }
  }, [])

  return {
    isPlaying,
    isBuffering,
    currentPosition,
    duration,
    playChunk,
    playBase64Chunk,
    playStoredAudio,
    stop,
    pause,
    resume,
    currentAudioUrl: currentUrlRef.current
  }
}