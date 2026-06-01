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
  startRecording: () => Promise<void>
  stopRecording: () => Promise<string>
  playAudio: (base64Audio: string) => void
  stopPlaying: () => void
  stopVAD: () => void
  setVADOptions: (options: { vadThreshold?: number; silenceThreshold?: number }) => void
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

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })

      streamRef.current = stream

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

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorderRef.current.start(100)
      setIsRecording(true)
      updateAudioLevel()

    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }, [updateAudioLevel, startVAD])

  const stopRecording = useCallback(async (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!mediaRecorderRef.current || !isRecording) {
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
          resolve(base64)

        } catch (error) {
          reject(error)
        }
      }

      mediaRecorderRef.current.stop()
    })
  }, [isRecording, stopVADDetection])

  const playAudio = useCallback((base64Audio: string) => {
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current = null
    }

    const binaryString = atob(base64Audio)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }

    const blob = new Blob([bytes], { type: 'audio/mp3' })
    const url = URL.createObjectURL(blob)

    audioElementRef.current = new Audio(url)
    audioElementRef.current.onended = () => {
      setIsPlaying(false)
      URL.revokeObjectURL(url)
    }

    audioElementRef.current.play()
    setIsPlaying(true)
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