/**
 * PracticeReviewPage - Overall review and report page
 *
 * Features:
 * - Radar chart for multi-dimensional scores
 * - Key strengths and areas for improvement
 * - Practice history comparison
 * - PDF report export
 * - Next practice focus suggestions
 *
 * Story: 1.4 整体复盘与报告
 */
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ScoreChart from '../../components/business/practice/ScoreChart'
import api from '../../api/practice'

interface StageDetail {
  quote?: string
  analysis?: string
  reference?: string
  suggestion?: string
}

interface ReviewData {
  session_id: string
  overall_score: number
  situation_score: number
  problem_score: number
  implication_score: number
  need_payoff_score: number
  communication_score: number
  persuasion_score: number
  closing_score: number
  spin_score: number
  // 4 维度详细评价（来自 LLM 真实输出）
  situation?: StageDetail
  problem?: StageDetail
  implication?: StageDetail
  need_payoff?: StageDetail
  key_strengths: string[]
  areas_for_improvement: string[]
  next_practice_focus: string
  created_at: string
}

interface PracticeReviewPageProps {
  sessionId?: string
}

const PracticeReviewPage = ({ sessionId: propSessionId }: PracticeReviewPageProps) => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const sessionIdFromUrl = searchParams.get('sessionId')
  const sessionId = propSessionId || sessionIdFromUrl

  const [reviewData, setReviewData] = useState<ReviewData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'strengths' | 'improvements'>('strengths')

  useEffect(() => {
    const loadReview = async () => {
      setIsLoading(true)
      setLoadError(null)

      if (!sessionId) {
        // 无 sessionId：直接重定向回练习页，不要渲染假报告
        navigate('/practice', { replace: true })
        return
      }

      try {
        const summary = await api.getSessionSummary(sessionId)
        setReviewData({
          session_id: summary.session_id,
          overall_score: summary.overall_score,
          situation_score: summary.situation_score,
          problem_score: summary.problem_score,
          implication_score: summary.implication_score,
          need_payoff_score: summary.need_payoff_score,
          // 后端目前没通信/说服/促成子分；显示 null 让 UI 显示 "-"
          // 不要硬编码 75 占位
          communication_score: (summary as any).communication_score ?? null,
          persuasion_score: (summary as any).persuasion_score ?? null,
          closing_score: (summary as any).closing_score ?? null,
          spin_score: (summary as any).spin_score ?? summary.overall_score,
          // 后端缺字段时显示空数组（UI 已能渲染"暂无"）
          key_strengths: summary.key_strengths || [],
          areas_for_improvement: summary.areas_for_improvement || [],
          next_practice_focus: summary.next_practice_focus || '',
          created_at: new Date().toISOString()
        })
      } catch (error: any) {
        console.error('Failed to load session summary:', error)
        setLoadError(
          error?.response?.data?.detail || error?.message || '加载复盘失败'
        )
        setReviewData(null)
      } finally {
        setIsLoading(false)
      }
    }
    loadReview()
  }, [sessionId, navigate])

  const handleExportPDF = async () => {
    if (!sessionId) return
    // 后端已有 /practice/sessions/{id}/report/pdf 真实接口
    try {
      await api.downloadReportPdf(sessionId)
    } catch (error: any) {
      console.error('PDF download failed:', error)
      alert('PDF 导出失败：' + (error?.response?.data?.detail || error?.message || '未知错误'))
    }
  }

  const handlePracticeAgain = () => {
    navigate('/practice')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-gray-500">加载复盘数据...</p>
        </div>
      </div>
    )
  }

  if (loadError || !reviewData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-xl p-8 shadow-sm text-center max-w-md">
          <p className="text-red-600 mb-4">{loadError || '复盘数据不存在'}</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-primary text-white rounded-lg"
            >
              重试
            </button>
            <button
              onClick={handlePracticeAgain}
              className="px-4 py-2 border border-gray-300 rounded-lg"
            >
              返回练习
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!reviewData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">暂无复盘数据</p>
          <button onClick={() => navigate('/practice')} className="mt-4 text-primary hover:underline">
            返回对练
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">对练复盘</h1>
              <p className="text-sm text-gray-500 mt-1">
                {new Date(reviewData.created_at).toLocaleDateString('zh-CN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </p>
            </div>
            <button
              onClick={() => navigate('/practice')}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Score Card */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">能力评估</h2>
          <ScoreChart scores={reviewData as any} />
        </div>

        {/* SPIN 4 维度详细评价（来自 LLM） */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📋 SPIN 四维详细评价</h2>
          <div className="space-y-3">
            {[
              { key: 'situation', label: 'S-现状探询', desc: '询问客户当前背景' },
              { key: 'problem', label: 'P-难点发掘', desc: '挖出客户具体不满' },
              { key: 'implication', label: 'I-暗示后果', desc: '放大问题影响' },
              { key: 'need_payoff', label: 'N-价值呈现', desc: '让客户自己说价值' },
            ].map((stage) => {
              const detail = (reviewData as any)[stage.key] as StageDetail | undefined
              if (!detail || (!detail.quote && !detail.analysis && !detail.reference && !detail.suggestion)) {
                return null
              }
              return (
                <details key={stage.key} className="border border-gray-200 rounded-lg">
                  <summary className="cursor-pointer p-3 font-medium text-gray-800 hover:bg-gray-50">
                    {stage.label} <span className="text-xs text-gray-500 ml-2">- {stage.desc}</span>
                  </summary>
                  <div className="px-3 pb-3 space-y-2 text-sm">
                    {detail.quote && (
                      <div className="bg-blue-50 border-l-2 border-blue-400 p-2">
                        <div className="text-xs text-blue-600 font-medium">📌 销售员原话</div>
                        <div className="text-gray-700 italic">"{detail.quote}"</div>
                      </div>
                    )}
                    {detail.analysis && (
                      <div className="px-2">
                        <div className="text-xs text-gray-500 font-medium">💡 评分原因</div>
                        <div className="text-gray-700">{detail.analysis}</div>
                      </div>
                    )}
                    {detail.reference && (
                      <div className="bg-amber-50 border-l-2 border-amber-400 p-2">
                        <div className="text-xs text-amber-700 font-medium">📚 知识库依据</div>
                        <div className="text-gray-700">{detail.reference}</div>
                      </div>
                    )}
                    {detail.suggestion && (
                      <div className="bg-green-50 border-l-2 border-green-400 p-2">
                        <div className="text-xs text-green-700 font-medium">✅ 改进建议</div>
                        <div className="text-gray-700">{detail.suggestion}</div>
                      </div>
                    )}
                  </div>
                </details>
              )
            })}
          </div>
        </div>

        {/* Strengths & Improvements */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setActiveTab('strengths')}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${activeTab === 'strengths'
                  ? 'bg-success text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
            >
              做得好 ({reviewData.key_strengths.length})
            </button>
            <button
              onClick={() => setActiveTab('improvements')}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${activeTab === 'improvements'
                  ? 'bg-warning text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
            >
              需改进 ({reviewData.areas_for_improvement.length})
            </button>
          </div>

          <div className="space-y-3">
            {activeTab === 'strengths' && reviewData.key_strengths.map((item, idx) => (
              <div key={idx} className="flex gap-3 p-4 bg-success/5 rounded-lg border border-success/20">
                <div className="flex-shrink-0 w-8 h-8 bg-success/10 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-gray-700">{item}</p>
              </div>
            ))}

            {activeTab === 'improvements' && reviewData.areas_for_improvement.map((item, idx) => (
              <div key={idx} className="flex gap-3 p-4 bg-warning/5 rounded-lg border border-warning/20">
                <div className="flex-shrink-0 w-8 h-8 bg-warning/10 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <p className="text-gray-700">{item}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Next Practice Focus */}
        <div className="bg-gradient-to-r from-primary/5 to-secondary/5 rounded-xl p-6 border border-primary/20">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">下次练习重点</h3>
              <p className="text-gray-700">{reviewData.next_practice_focus}</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={handlePracticeAgain}
            className="flex-1 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 font-medium transition-all"
          >
            再练一次
          </button>
          <button
            onClick={handleExportPDF}
            className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-all flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            导出报告
          </button>
        </div>
      </main>
    </div>
  )
}

export default PracticeReviewPage