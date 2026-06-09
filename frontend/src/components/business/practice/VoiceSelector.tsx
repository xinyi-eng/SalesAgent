/**
 * VoiceSelector Component
 *
 * MiniMax TTS voice selection with preview functionality.
 *
 * Voice Categories:
 * - Chinese Male: Reliable Executive (稳重高管)
 * - Chinese Female: News Anchor (新闻主播), Lyrical (抒情)
 * - English: Various voices for different character types
 */
import { useState } from 'react'

// MiniMax TTS voice definitions
export const VOICE_OPTIONS = [
  // Chinese voices
  {
    id: 'Chinese (Mandarin)_Reliable_Executive',
    name: '稳重高管',
    description: '稳重可信赖的企业高管声音',
    language: 'zh',
    gender: 'male',
    recommendedFor: ['senior', 'decisive', 'value_oriented']
  },
  {
    id: 'Chinese (Mandarin)_News_Anchor',
    name: '新闻主播',
    description: '专业播音风格中年女性',
    language: 'zh',
    gender: 'female',
    recommendedFor: ['middle', 'rational', 'value_oriented']
  },
  {
    id: 'Chinese (Mandarin)_Lyrical_Voice',
    name: '抒情女声',
    description: '温和抒情的女性声音',
    language: 'zh',
    gender: 'female',
    recommendedFor: ['junior', 'hesitant', 'relationship_oriented']
  },
  {
    id: 'Chinese (Mandarin)_HK_Flight_Attendant',
    name: '香港乘务',
    description: '香港空乘风格的亲切声音',
    language: 'zh',
    gender: 'female',
    recommendedFor: ['middle', 'emotional', 'relationship_oriented']
  },
  // English voices
  {
    id: 'English_Graceful_Lady',
    name: '优雅女士',
    description: '优雅的英式女性声音',
    language: 'en',
    gender: 'female',
    recommendedFor: ['middle', 'emotional', 'relationship_oriented']
  },
  {
    id: 'English_Insightful_Speaker',
    name: '洞察演讲者',
    description: '理性有洞察力的演讲者',
    language: 'en',
    gender: 'male',
    recommendedFor: ['senior', 'rational', 'value_oriented']
  },
  {
    id: 'English_Persuasive_Man',
    name: '说服力男性',
    description: '有说服力的男性声音',
    language: 'en',
    gender: 'male',
    recommendedFor: ['senior', 'decisive', 'price_oriented']
  },
  {
    id: 'English_radiant_girl',
    name: '活泼女孩',
    description: '活力四射的年轻女性',
    language: 'en',
    gender: 'female',
    recommendedFor: ['junior', 'emotional', 'relationship_oriented']
  },
  {
    id: 'English_expressive_narrator',
    name: '表达叙述者',
    description: '富有表现力的叙述者',
    language: 'en',
    gender: 'male',
    recommendedFor: ['middle', 'rational', 'value_oriented']
  },
  // Japanese voice
  {
    id: 'Japanese_Whisper_Belle',
    name: '耳语美女',
    description: '轻柔的日语耳语风格',
    language: 'ja',
    gender: 'female',
    recommendedFor: ['junior', 'hesitant', 'relationship_oriented']
  },
  // Default fallback
  {
    id: 'male-qn-qingse',
    name: '默认男声',
    description: '系统默认男性声音',
    language: 'zh',
    gender: 'male',
    recommendedFor: []
  }
]

interface VoiceSelectorProps {
  selectedVoice: string | null
  onChange: (voice: string) => void
  positionLevel?: string
  personality?: string
  decisionStyle?: string
  isDisabled?: boolean
}

// Get recommended voice based on role configuration
export function getRecommendedVoice(positionLevel?: string, personality?: string, decisionStyle?: string): string {
  // Find matching voices based on role config
  const recommended = VOICE_OPTIONS.find(voice => {
    if (positionLevel && voice.recommendedFor.includes(positionLevel)) return true
    if (personality && voice.recommendedFor.includes(personality)) return true
    if (decisionStyle && voice.recommendedFor.includes(decisionStyle)) return true
    return false
  })
  return recommended?.id || 'Chinese (Mandarin)_Reliable_Executive'
}

const VoiceSelector = ({
  selectedVoice,
  onChange,
  positionLevel,
  personality,
  decisionStyle,
  isDisabled = false
}: VoiceSelectorProps) => {
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false)
  const [previewVoiceId, setPreviewVoiceId] = useState<string | null>(null)

  const recommendedVoice = getRecommendedVoice(positionLevel, personality, decisionStyle)

  const handlePreview = async (voiceId: string) => {
    if (isPreviewPlaying) return

    setIsPreviewPlaying(true)
    setPreviewVoiceId(voiceId)

    try {
      // Call TTS preview API
      const response = await fetch('/api/v1/tts/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voice_id: voiceId,
          text: '您好，我是您的AI模拟客户。让我来了解一下您的产品。'
        })
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)

        audio.onended = () => {
          setIsPreviewPlaying(false)
          setPreviewVoiceId(null)
          URL.revokeObjectURL(url)
        }

        audio.onerror = () => {
          setIsPreviewPlaying(false)
          setPreviewVoiceId(null)
        }

        await audio.play()
      }
    } catch (error) {
      console.error('Preview failed:', error)
      setIsPreviewPlaying(false)
      setPreviewVoiceId(null)
    }
  }

  const handleSelect = (voiceId: string) => {
    if (isDisabled) return
    onChange(voiceId)
  }

  // Group voices by language
  const chineseVoices = VOICE_OPTIONS.filter(v => v.language === 'zh')
  const englishVoices = VOICE_OPTIONS.filter(v => v.language === 'en')
  const otherVoices = VOICE_OPTIONS.filter(v => v.language !== 'zh' && v.language !== 'en')

  const renderVoiceOption = (voice: typeof VOICE_OPTIONS[0]) => {
    const isSelected = selectedVoice === voice.id
    const isRecommended = voice.id === recommendedVoice && !selectedVoice
    const isPlaying = isPreviewPlaying && previewVoiceId === voice.id

    return (
      <div
        key={voice.id}
        role="button"
        tabIndex={isDisabled ? -1 : 0}
        onClick={() => handleSelect(voice.id)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handleSelect(voice.id)
          }
        }}
        aria-pressed={isSelected}
        className={`
          relative p-3 rounded-lg border-2 text-left transition-all duration-200
          ${isSelected
            ? 'border-primary bg-blue-50'
            : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
          }
          ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-gray-900 flex items-center gap-2">
              {voice.name}
              {isRecommended && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                  推荐
                </span>
              )}
              {voice.language === 'en' && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                  EN
                </span>
              )}
              {voice.language === 'ja' && (
                <span className="text-xs bg-pink-100 text-pink-700 px-2 py-0.5 rounded-full">
                  JA
                </span>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">{voice.description}</div>
          </div>

          {/* Preview button */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              handlePreview(voice.id)
            }}
            disabled={isDisabled || isPlaying}
            className={`
              p-2 rounded-full transition-colors
              ${isPlaying
                ? 'bg-primary text-white animate-pulse'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
              }
            `}
            title="预览声线"
          >
            {isPlaying ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            )}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-gray-700">
            AI客户声线 <span className="text-red-500">*</span>
          </label>
          {!selectedVoice && (
            <button
              onClick={() => onChange(recommendedVoice)}
              className="text-sm text-primary hover:underline"
            >
              使用推荐声线
            </button>
          )}
        </div>

        {/* Chinese Voices */}
        <div className="mb-4">
          <div className="text-xs text-gray-500 mb-2">中文声线</div>
          <div className="grid grid-cols-1 gap-2">
            {chineseVoices.map(renderVoiceOption)}
          </div>
        </div>

        {/* English Voices */}
        <div className="mb-4">
          <div className="text-xs text-gray-500 mb-2">英文声线</div>
          <div className="grid grid-cols-1 gap-2">
            {englishVoices.map(renderVoiceOption)}
          </div>
        </div>

        {/* Other Voices */}
        {otherVoices.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-2">其他声线</div>
            <div className="grid grid-cols-1 gap-2">
              {otherVoices.map(renderVoiceOption)}
            </div>
          </div>
        )}
      </div>

      {/* Current selection */}
      {selectedVoice && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm text-gray-500">已选择：</span>
              <span className="text-sm font-medium text-gray-900">
                {VOICE_OPTIONS.find(v => v.id === selectedVoice)?.name || selectedVoice}
              </span>
            </div>
            <button
              onClick={() => handlePreview(selectedVoice)}
              disabled={isDisabled || isPreviewPlaying}
              className="text-sm text-primary hover:underline disabled:opacity-50"
            >
              {isPreviewPlaying ? '播放中...' : '再次预览'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default VoiceSelector
