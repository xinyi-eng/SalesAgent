/**
 * ScoreChart Component
 *
 * Radar chart showing scores across multiple dimensions:
 * - 沟通能力 (Communication)
 * - 说服能力 (Persuasion)
 * - 促成能力 (Closing)
 * - 扭转能力 (Spin)
 */
import { useEffect, useRef } from 'react'

interface ScoreData {
  communication_score: number
  persuasion_score: number
  closing_score: number
  spin_score: number
}

interface ScoreChartProps {
  scores: ScoreData
  size?: number
}

const ScoreChart = ({ scores, size = 280 }: ScoreChartProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const centerX = size / 2
    const centerY = size / 2
    const radius = size / 2 - 40

    // Clear canvas
    ctx.clearRect(0, 0, size, size)

    // Draw background rings
    const labels = ['沟通能力', '说服能力', '促成能力', '扭转能力']
    const numAxes = labels.length
    const angleStep = (2 * Math.PI) / numAxes

    // Draw concentric rings
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

    // Draw axes
    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2
      ctx.beginPath()
      ctx.moveTo(centerX, centerY)
      ctx.lineTo(centerX + radius * Math.cos(angle), centerY + radius * Math.sin(angle))
      ctx.strokeStyle = '#E5E7EB'
      ctx.stroke()
    }

    // Draw labels
    ctx.font = '12px system-ui, sans-serif'
    ctx.fillStyle = '#374151'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2
      const labelRadius = radius + 25
      const x = centerX + labelRadius * Math.cos(angle)
      const y = centerY + labelRadius * Math.sin(angle)
      ctx.fillText(labels[i], x, y)
    }

    // Draw score polygon
    const scoreValues = [scores.communication_score, scores.persuasion_score, scores.closing_score, scores.spin_score]

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
    ctx.fillStyle = 'rgba(37, 99, 235, 0.2)'
    ctx.fill()
    ctx.strokeStyle = '#2563EB'
    ctx.lineWidth = 2
    ctx.stroke()

    // Draw score points
    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2
      const value = (scoreValues[i] / 100) * radius
      const x = centerX + value * Math.cos(angle)
      const y = centerY + value * Math.sin(angle)

      ctx.beginPath()
      ctx.arc(x, y, 5, 0, 2 * Math.PI)
      ctx.fillStyle = '#2563EB'
      ctx.fill()
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    // Draw center score
    const overallScore = ((scores.communication_score + scores.persuasion_score + scores.closing_score + scores.spin_score) / 4).toFixed(1)
    ctx.font = 'bold 32px system-ui, sans-serif'
    ctx.fillStyle = '#2563EB'
    ctx.fillText(overallScore, centerX, centerY - 8)
    ctx.font = '12px system-ui, sans-serif'
    ctx.fillStyle = '#6B7280'
    ctx.fillText('综合得分', centerX, centerY + 16)
  }, [scores, size])

  return (
    <div className="flex flex-col items-center">
      <canvas ref={canvasRef} width={size} height={size} className="max-w-full" />
      <div className="grid grid-cols-2 gap-4 mt-4 w-full px-8">
        {[
          { label: '沟通能力', value: scores.communication_score, color: '#2563EB' },
          { label: '说服能力', value: scores.persuasion_score, color: '#7C3AED' },
          { label: '促成能力', value: scores.closing_score, color: '#059669' },
          { label: '扭转能力', value: scores.spin_score, color: '#DC2626' }
        ].map(item => (
          <div key={item.label} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-sm text-gray-600">{item.label}</span>
            <span className="text-sm font-semibold text-gray-900 ml-auto">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ScoreChart