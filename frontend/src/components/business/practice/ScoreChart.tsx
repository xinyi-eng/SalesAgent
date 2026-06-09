/**
 * ScoreChart Component — Radar chart for 6 维能力评估
 *
 * 维度定义（与 PrePracticeForm 的 practice_goals 对齐）：
 * - 开场破冰
 * - 需求挖掘
 * - 产品呈现
 * - 异议处理
 * - 促成成交
 * - 关系建立
 *
 * 接收 scores 字典 {维度名: 0-100分}，自适应渲染
 */
import { useEffect, useRef } from 'react'

type ScoreData = Record<string, number | undefined | null>

interface ScoreChartProps {
  scores: ScoreData
  size?: number
  dimensions?: Array<{ key: string; label: string; color: string }>
}

const DEFAULT_DIMENSIONS = [
  { key: 'opening',   label: '开场破冰', color: '#10B981' },
  { key: 'discovery', label: '需求挖掘', color: '#3B82F6' },
  { key: 'presentation', label: '产品呈现', color: '#F59E0B' },
  { key: 'objection', label: '异议处理', color: '#EF4444' },
  { key: 'closing',   label: '促成成交', color: '#8B5CF6' },
  { key: 'rapport',   label: '关系建立', color: '#EC4899' },
]

// 把后端的 communication/persuasion/closing/spin 4 维映射到 6 维
// (这是临时映射，等后端 /practice/sessions/{id}/summary 改成 6 维后就直接读)
const LEGACY_KEY_MAP: Record<string, string> = {
  'communication_score': 'opening',
  'persuasion_score': 'discovery',
  'closing_score': 'closing',
  'spin_score': 'objection',
}

function resolveScore(scores: ScoreData, key: string): number {
  if (typeof scores[key] === 'number') return scores[key] as number
  // 兼容旧的 4 维字段
  for (const [legacyKey, mappedKey] of Object.entries(LEGACY_KEY_MAP)) {
    if (mappedKey === key && typeof scores[legacyKey] === 'number') {
      return scores[legacyKey] as number
    }
  }
  return 0
}

const ScoreChart = ({ scores, size = 320, dimensions = DEFAULT_DIMENSIONS }: ScoreChartProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const centerX = size / 2
    const centerY = size / 2
    const radius = size / 2 - 50  // 留更多空间给 label

    ctx.clearRect(0, 0, size, size)

    const numAxes = dimensions.length
    const angleStep = (2 * Math.PI) / numAxes
    const labels = dimensions.map(d => d.label)
    const scoreValues = dimensions.map(d => resolveScore(scores, d.key))

    // 同心圆
    for (let ring = 1; ring <= 5; ring++) {
      const ringRadius = (radius * ring) / 5
      ctx.beginPath()
      for (let i = 0; i <= numAxes; i++) {
        const angle = i * angleStep - Math.PI / 2
        const x = centerX + ringRadius * Math.cos(angle)
        const y = centerY + ringRadius * Math.sin(angle)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.strokeStyle = '#E5E7EB'
      ctx.stroke()
    }

    // 轴线
    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2
      ctx.beginPath()
      ctx.moveTo(centerX, centerY)
      ctx.lineTo(centerX + radius * Math.cos(angle), centerY + radius * Math.sin(angle))
      ctx.strokeStyle = '#E5E7EB'
      ctx.stroke()
    }

    // 标签
    ctx.font = '13px system-ui, sans-serif'
    ctx.fillStyle = '#374151'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2
      const labelRadius = radius + 30
      const x = centerX + labelRadius * Math.cos(angle)
      const y = centerY + labelRadius * Math.sin(angle)
      ctx.fillText(labels[i], x, y)
    }

    // 分数多边形
    ctx.beginPath()
    for (let i = 0; i <= numAxes; i++) {
      const idx = i % numAxes
      const angle = idx * angleStep - Math.PI / 2
      const value = (scoreValues[idx] / 100) * radius
      const x = centerX + value * Math.cos(angle)
      const y = centerY + value * Math.sin(angle)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.closePath()
    ctx.fillStyle = 'rgba(59, 130, 246, 0.2)'
    ctx.fill()
    ctx.strokeStyle = '#3B82F6'
    ctx.lineWidth = 2
    ctx.stroke()

    // 数据点
    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2
      const value = (scoreValues[i] / 100) * radius
      const x = centerX + value * Math.cos(angle)
      const y = centerY + value * Math.sin(angle)
      ctx.beginPath()
      ctx.arc(x, y, 5, 0, 2 * Math.PI)
      ctx.fillStyle = '#3B82F6'
      ctx.fill()
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    // 中心综合分
    const validScores = scoreValues.filter(s => s > 0)
    const overallScore = validScores.length > 0
      ? (validScores.reduce((a, b) => a + b, 0) / validScores.length).toFixed(1)
      : '0'
    ctx.font = 'bold 32px system-ui, sans-serif'
    ctx.fillStyle = '#3B82F6'
    ctx.fillText(overallScore, centerX, centerY - 8)
    ctx.font = '12px system-ui, sans-serif'
    ctx.fillStyle = '#6B7280'
    ctx.fillText('综合得分', centerX, centerY + 16)
  }, [scores, size, dimensions])

  return (
    <div className="flex flex-col items-center">
      <canvas ref={canvasRef} width={size} height={size} className="max-w-full" />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2 mt-4 w-full px-4">
        {dimensions.map((dim) => (
          <div key={dim.key} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: dim.color }}
            />
            <span className="text-gray-600 truncate">{dim.label}</span>
            <span className="text-sm font-semibold text-gray-900 ml-auto">
              {resolveScore(scores, dim.key)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ScoreChart
