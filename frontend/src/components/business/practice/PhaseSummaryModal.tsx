/**
 * PhaseSummaryModal Component
 *
 * Displays AI-generated phase summary with:
 * - Good points (做得好的地方)
 * - Improvements (需要改进的地方)
 * - Suggestions (改进建议)
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface PhaseSummaryData {
  phase: string
  phase_label: string
  overall_score?: number
  situation_score?: number
  problem_score?: number
  implication_score?: number
  need_payoff_score?: number
  good_points: string[]
  improvements: string[]
  suggestions: string[]
}

interface PhaseSummaryModalProps {
  isOpen: boolean
  onClose: () => void
  summary: PhaseSummaryData | null
  isLoading?: boolean
  sessionId?: string
}

const PhaseSummaryModal = ({ isOpen, onClose, summary, isLoading = false, sessionId }: PhaseSummaryModalProps) => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<'good' | 'improve' | 'suggest'>('good')

  const handleViewFullReport = () => {
    if (sessionId) {
      navigate(`/practice/report/${sessionId}`)
    }
  }

  useEffect(() => {
    if (isOpen) {
      setActiveTab('good')
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg transform transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {isLoading ? '生成中...' : '阶段总结'}
              </h3>
              {!isLoading && summary && (
                <p className="text-sm text-gray-500 mt-0.5">
                  {summary.phase_label}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-8">
                <div className="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                <p className="mt-4 text-gray-500">AI正在分析对话内容...</p>
              </div>
            ) : summary ? (
              <>
                {/* SPIN Scores */}
                {(summary.overall_score !== undefined && summary.overall_score > 0) && (
                  <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-700 mb-2">本阶段SPIN评分</div>
                    <div className="grid grid-cols-4 gap-2 text-center">
                      <div>
                        <div className="text-lg font-bold text-primary">{summary.situation_score || 0}</div>
                        <div className="text-xs text-gray-500">现状了解</div>
                      </div>
                      <div>
                        <div className="text-lg font-bold text-secondary">{summary.problem_score || 0}</div>
                        <div className="text-xs text-gray-500">痛点发现</div>
                      </div>
                      <div>
                        <div className="text-lg font-bold text-warning">{summary.implication_score || 0}</div>
                        <div className="text-xs text-gray-500">影响放大</div>
                      </div>
                      <div>
                        <div className="text-lg font-bold text-success">{summary.need_payoff_score || 0}</div>
                        <div className="text-xs text-gray-500">价值认同</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tabs */}
                <div className="flex gap-2 mb-4">
                  {[
                    { key: 'good', label: '做得好', count: (summary.good_points || []).length },
                    { key: 'improve', label: '需改进', count: (summary.improvements || []).length },
                    { key: 'suggest', label: '建议', count: (summary.suggestions || []).length }
                  ].map(tab => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key as typeof activeTab)}
                      className={`
                        px-4 py-2 rounded-lg text-sm font-medium transition-all
                        ${activeTab === tab.key
                          ? 'bg-primary text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }
                      `}
                    >
                      {tab.label} ({tab.count})
                    </button>
                  ))}
                </div>

                {/* Tab Content */}
                <div className="space-y-3">
                  {activeTab === 'good' && (summary.good_points || []).map((point, idx) => (
                    <div key={idx} className="flex gap-3 p-3 bg-success/5 rounded-lg border border-success/20">
                      <div className="flex-shrink-0 w-6 h-6 bg-success/10 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <p className="text-sm text-gray-700">{point}</p>
                    </div>
                  ))}

                  {activeTab === 'improve' && (summary.improvements || []).map((point, idx) => (
                    <div key={idx} className="flex gap-3 p-3 bg-warning/5 rounded-lg border border-warning/20">
                      <div className="flex-shrink-0 w-6 h-6 bg-warning/10 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                      </div>
                      <p className="text-sm text-gray-700">{point}</p>
                    </div>
                  ))}

                  {activeTab === 'suggest' && (summary.suggestions || []).map((point, idx) => (
                    <div key={idx} className="flex gap-3 p-3 bg-primary/5 rounded-lg border border-primary/20">
                      <div className="flex-shrink-0 w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                      </div>
                      <p className="text-sm text-gray-700">{point}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                暂无总结数据
              </div>
            )}
          </div>

          {/* Footer */}
          {!isLoading && summary && (
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                继续对练
              </button>
              <button
                onClick={handleViewFullReport}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
              >
                查看完整报告
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PhaseSummaryModal