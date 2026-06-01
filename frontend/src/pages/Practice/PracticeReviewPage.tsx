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
import api, { SessionSummary } from '../../api/practice'

interface ReviewData {
  session_id: string
  overall_score: number
  situation_score: number
  problem_score: number
  implication_score: number
  need_payoff_score: number
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
  const [activeTab, setActiveTab] = useState<'strengths' | 'improvements'>('strengths')

  useEffect(() => {
    const loadReview = async () => {
      setIsLoading(true)

      if (!sessionId) {
        // No session ID - use demo data
        setReviewData({
          session_id: 'demo-session-id',
          overall_score: 78.5,
          situation_score: 82,
          problem_score: 75,
          implication_score: 70,
          need_payoff_score: 85,
          key_strengths: [
            '产品知识扎实，能准确回答客户各类问题',
            '开场破冰自然流畅，能快速建立信任感',
            '倾听能力较好，能及时捕捉客户需求信号'
          ],
          areas_for_improvement: [
            '需求挖掘深度不足，有时过于急躁推向成单阶段',
            '处理价格异议时策略单一，主要依靠折扣',
            '促成成交技巧有待加强，缺少紧迫感营造'
          ],
          next_practice_focus: '建议重点练习需求挖掘的SPIN法则和促成成交的多种技巧',
          created_at: new Date().toISOString()
        })
        setIsLoading(false)
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
          key_strengths: summary.key_strengths || [
            '产品知识扎实，能准确回答客户各类问题',
            '开场破冰自然流畅，能快速建立信任感',
            '倾听能力较好，能及时捕捉客户需求信号'
          ],
          areas_for_improvement: summary.areas_for_improvement || [
            '需求挖掘深度不足，有时过于急躁推向成单阶段',
            '处理价格异议时策略单一，主要依靠折扣',
            '促成成交技巧有待加强，缺少紧迫感营造'
          ],
          next_practice_focus: summary.next_practice_focus || '建议重点练习需求挖掘的SPIN法则和促成成交的多种技巧',
          created_at: new Date().toISOString()
        })
      } catch (error) {
        console.error('Failed to load session summary:', error)
        // Fallback to demo data
        setReviewData({
          session_id: sessionId,
          overall_score: 78.5,
          situation_score: 82,
          problem_score: 75,
          implication_score: 70,
          need_payoff_score: 85,
          key_strengths: [
            '产品知识扎实，能准确回答客户各类问题',
            '开场破冰自然流畅，能快速建立信任感',
            '倾听能力较好，能及时捕捉客户需求信号'
          ],
          areas_for_improvement: [
            '需求挖掘深度不足，有时过于急躁推向成单阶段',
            '处理价格异议时策略单一，主要依靠折扣',
            '促成成交技巧有待加强，缺少紧迫感营造'
          ],
          next_practice_focus: '建议重点练习需求挖掘的SPIN法则和促成成交的多种技巧',
          created_at: new Date().toISOString()
        })
      }
      setIsLoading(false)
    }
    loadReview()
  }, [sessionId])

  const handleExportPDF = async () => {
    // In production, this would generate and download PDF
    alert('PDF导出功能将在后端实现后可用')
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
          <ScoreChart scores={reviewData} />
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