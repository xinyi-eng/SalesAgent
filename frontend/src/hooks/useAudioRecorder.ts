/**
 * useAudioRecorder - Hook for recording and playing audio
 * Enhanced with VAD integration and audio processing
 */
import { useState, useRef, useCallback } from 'react'
import { useVAD } from './useVAD'

interface UseAudioRecorderReturn {
  isRecording: boolean
  isPlaying: boolean
  isVoiceDetected: boolean
  audioLevel: number
  startRecording: (opts?: { onChunk?: (chunk: Uint8Array) => void }) => Promise<void>
  stopRecording: () => Promise<RecordedAudio>
  playAudio: (base64Audio: string) => void
  stopPlaying: () => void
  stopVAD: () => void
  setVADOptions: (options: { vadThreshold?: number; silenceThreshold?: number }) => void
}

export interface RecordedAudio {
  /** Base64 encoded audio data (webm/opus) */
  audio: string
  /** Length of the recording in milliseconds */
  durationMs: number
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const audioElementRef = useRef<HTMLAudioElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recordingStartRef = useRef<number | null>(null)

  const { isVoiceDetected, startVAD, stopVAD: stopVADDetection, setOptions: setVADOptions } = useVAD()

  const updateAudioLevel = useCallback(() => {
    if (analyserRef.current && isRecording) {
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
      analyserRef.current.getByteFrequencyData(dataArray)

      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
      setAudioLevel(average / 255)

      animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
    }
  }, [isRecording])

  const startRecording = useCallback(async (opts?: { onChunk?: (chunk: Uint8Array) => void }) => {
    const startTime = Date.now()
    const onChunk = opts?.onChunk
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })

      streamRef.current = stream
      recordingStartRef.current = startTime

      // Set up audio analysis for level meter
      audioContextRef.current = new AudioContext()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256
      source.connect(analyserRef.current)

      // Start VAD for voice detection
      startVAD(stream)

      // Start recording
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
          // 流式推送：把每个分片立刻转成 Uint8Array 通过 onChunk 回调
          // （由调用方负责通过 WebSocket 二进制帧推到后端，让后端做实时 ASR）
          if (onChunk) {
            try {
              const buf = await event.data.arrayBuffer()
              onChunk(new Uint8Array(buf))
            } catch (e) {
              console.error('[Recorder] failed to push chunk:', e)
            }
          }
        }
      }

      mediaRecorderRef.current.start(200)  // 200ms 一片 → 平衡延迟与开销
      setIsRecording(true)
      updateAudioLevel()

    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }, [updateAudioLevel, startVAD])

  const stopRecording = useCallback(async (): Promise<RecordedAudio> => {
    return new Promise((resolve, reject) => {
      // Use the ref-backed recorder (state-based `isRecording` may be stale
      // in fast mousedown/mouseup sequences).
      if (!mediaRecorderRef.current) {
        reject(new Error('Not recording'))
        return
      }

      mediaRecorderRef.current.onstop = async () => {
        try {
          // Stop all tracks
          mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop())
          streamRef.current?.getTracks().forEach(track => track.stop())

          // Stop VAD
          stopVADDetection()

          // Stop audio context
          if (audioContextRef.current) {
            audioContextRef.current.close()
            audioContextRef.current = null
          }

          // Cancel animation frame
          if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current)
            animationFrameRef.current = null
          }

          setAudioLevel(0)
          setIsRecording(false)

          // Convert to base64
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
          const arrayBuffer = await audioBlob.arrayBuffer()
          const base64 = arrayBufferToBase64(arrayBuffer)
          const durationMs = recordingStartRef.current
            ? Date.now() - recordingStartRef.current
            : 0
          resolve({ audio: base64, durationMs })

        } catch (error) {
          reject(error)
        }
      }

      mediaRecorderRef.current.stop()
    })
  }, [stopVADDetection])

  const playAudio = useCallback((base64Audio: string) => {
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current = null
    }

    if (!base64Audio || base64Audio.length === 0) {
      console.error('[Replay] No audio data to play')
      return
    }

    console.log('[Replay] Playing audio, length:', base64Audio.length)

    try {
      // Decode base64
      const binaryString = atob(base64Audio)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      console.log('[Replay] Decoded bytes:', bytes.length)

      // Try HTML5 Audio first with mp3
      const blob = new Blob([bytes], { type: 'audio/mpeg' })
      const url = URL.createObjectURL(blob)

      audioElementRef.current = new Audio(url)

      audioElementRef.current.onloadedmetadata = () => {
        console.log('[Replay] Audio duration:', audioElementRef.current?.duration)
      }

      audioElementRef.current.onplay = () => {
        console.log('[Replay] Playing!')
        setIsPlaying(true)
      }

      audioElementRef.current.onended = () => {
        console.log('[Replay] Ended')
        setIsPlaying(false)
        URL.revokeObjectURL(url)
      }

      audioElementRef.current.onerror = (e) => {
        console.error('[Replay] Audio error:', audioElementRef.current?.error)
        // Try as raw PCM if mp3 fails
        tryRawPCM(bytes)
      }

      audioElementRef.current.play().catch(err => {
        console.error('[Replay] Play error:', err)
        tryRawPCM(bytes)
      })
    } catch (e) {
      console.error('[Replay] Failed to decode base64:', e)
      // Try raw PCM directly
      tryRawPCM(null)
    }

    function tryRawPCM(decodedBytes: Uint8Array | null) {
      console.log('[Replay] Trying raw PCM playback...')
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
        if (!AudioContextClass) {
          console.error('[Replay] No AudioContext')
          return
        }

        const ctx = new AudioContextClass()
        const sampleRate = 32000
        const numChannels = 1

        let bytesToUse = decodedBytes
        if (!bytesToUse) {
          console.error('[Replay] No bytes available for PCM playback')
          return
        }

        const bytesPerSample = 2
        const numSamples = bytesToUse.length / bytesPerSample

        console.log('[Replay] Creating AudioBuffer:', numSamples, 'samples')
        const audioBuffer = ctx.createBuffer(numChannels, numSamples, sampleRate)
        const channelData = audioBuffer.getChannelData(0)

        const view = new DataView(bytesToUse.buffer, bytesToUse.byteOffset, bytesToUse.length)
        for (let i = 0; i < numSamples; i++) {
          const int16 = view.getInt16(i * 2, true)
          channelData[i] = int16 / 32768.0
        }

        const source = ctx.createBufferSource()
        source.buffer = audioBuffer
        source.connect(ctx.destination)
        source.start(0)
        setIsPlaying(true)

        source.onended = () => {
          console.log('[Replay] PCM playback ended')
          setIsPlaying(false)
          ctx.close()
        }
        console.log('[Replay] PCM playback started!')
      } catch (e) {
        console.error('[Replay] PCM playback failed:', e)
        setIsPlaying(false)
      }
    }
  }, [])

  const stopPlaying = useCallback(() => {
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current = null
    }
    setIsPlaying(false)
  }, [])

  return {
    isRecording,
    isPlaying,
    isVoiceDetected,
    audioLevel,
    startRecording,
    stopRecording,
    playAudio,
    stopPlaying,
    stopVAD: stopVADDetection,
    setVADOptions
  }
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}