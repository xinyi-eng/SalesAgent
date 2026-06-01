/**
 * useVAD - Voice Activity Detection hook
 * Uses Web Audio API AnalyserNode to detect voice and silence
 */
import { useState, useRef, useCallback, useEffect } from 'react'

interface VADOptions {
  vadThreshold?: number        // Energy threshold for voice detection (0-1)
  silenceThreshold?: number     // Silence duration before considered pause (ms)
  smoothingWindow?: number     // Number of frames to average
}

interface VADState {
  isVoiceDetected: boolean
  isSilence: boolean
  energyLevel: number
  silenceDuration: number
}

interface UseVADReturn extends VADState {
  startVAD: (audioStream: MediaStream) => void
  stopVAD: () => void
  setOptions: (options: VADOptions) => void
}

const DEFAULT_OPTIONS: VADOptions = {
  vadThreshold: 0.05,          // ~5% of max energy
  silenceThreshold: 1500,      // 1.5 seconds of silence
  smoothingWindow: 5
}

export function useVAD(options: VADOptions = DEFAULT_OPTIONS): UseVADReturn {
  const [state, setState] = useState<VADState>({
    isVoiceDetected: false,
    isSilence: true,
    energyLevel: 0,
    silenceDuration: 0
  })

  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const animationRef = useRef<number | null>(null)
  const energyHistoryRef = useRef<number[]>([])

  const currentOptions = useRef({ ...DEFAULT_OPTIONS, ...options })
  const silenceStartRef = useRef<number | null>(null)

  const calculateEnergy = useCallback((data: Uint8Array): number => {
    const sum = data.reduce((acc, val) => acc + (val * val), 0)
    return Math.sqrt(sum / data.length) / 255
  }, [])

  const smoothedEnergy = useCallback((energy: number): number => {
    const history = energyHistoryRef.current
    history.push(energy)
    if (history.length > currentOptions.current.smoothingWindow!) {
      history.shift()
    }
    return history.reduce((a, b) => a + b, 0) / history.length
  }, [])

  const detectVoice = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)

    const energy = smoothedEnergy(calculateEnergy(dataArray))
    const threshold = currentOptions.current.vadThreshold!

    const now = Date.now()
    const isVoice = energy > threshold

    setState(prev => {
      let newSilenceDuration = prev.silenceDuration
      let newIsSilence = prev.isSilence

      if (isVoice) {
        silenceStartRef.current = null
        newIsSilence = false
        newSilenceDuration = 0
      } else if (silenceStartRef.current === null) {
        silenceStartRef.current = now
      } else {
        newSilenceDuration = now - silenceStartRef.current
        newIsSilence = newSilenceDuration >= currentOptions.current.silenceThreshold!
      }

      return {
        isVoiceDetected: isVoice,
        isSilence: newIsSilence,
        energyLevel: energy,
        silenceDuration: newSilenceDuration
      }
    })

    animationRef.current = requestAnimationFrame(detectVoice)
  }, [smoothedEnergy, calculateEnergy])

  const startVAD = useCallback((audioStream: MediaStream) => {
    // Stop any existing VAD
    stopVAD()

    // Create audio context with echo cancellation and noise suppression
    audioContextRef.current = new AudioContext({
      // @ts-ignore - these are valid but not in all TS definitions
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    })

    const source = audioContextRef.current.createMediaStreamSource(audioStream)
    sourceRef.current = source

    const analyser = audioContextRef.current.createAnalyser()
    analyser.fftSize = 512
    analyser.smoothingTimeConstant = 0.3
    analyserRef.current = analyser

    source.connect(analyser)
    energyHistoryRef.current = []
    silenceStartRef.current = null

    detectVoice()
  }, [detectVoice])

  const stopVAD = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect()
      sourceRef.current = null
    }
    energyHistoryRef.current = []
    silenceStartRef.current = null

    setState({
      isVoiceDetected: false,
      isSilence: true,
      energyLevel: 0,
      silenceDuration: 0
    })
  }, [])

  const setOptions = useCallback((newOptions: VADOptions) => {
    currentOptions.current = { ...currentOptions.current, ...newOptions }
  }, [])

  useEffect(() => {
    return () => {
      stopVAD()
    }
  }, [stopVAD])

  return {
    ...state,
    startVAD,
    stopVAD,
    setOptions
  }
}