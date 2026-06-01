/**
 * ReportPage - 完整SPIN评价报告页面
 *
 * Features:
 * - 显示SPIN四步评分详情
 * - 显示知识引用作为评分依据
 * - 显示优点与改进建议
 * - 下次练习重点提示
 *
 * Story: 1.2 语音对话与实时交互
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../api/practice'

interface SpinScores {
  situation_score: number
  problem_score: number
  implication_score: number
  need_payoff_score: number
}

interface ReportData {
  session_id: string
  overall_score: number
  spin_scores: SpinScores
  key_strengths: string[]
  areas_for_improvement: string[]
  next_practice_focus: string
}

export default function ReportPage() {
  const { session_id } = useParams()
  const navigate = useNavigate()
  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadReport() {
      if (!session_id) {
        setError('会话ID不存在')
        setLoading(false)
        return
      }

      try {
        const data = await api.getSessionSummary(session_id)
        setReport(data)
      } catch (err) {
        console.error('Failed to load report:', err)
        setError('报告加载失败')
      } finally {
        setLoading(false)
      }
    }
    loadReport()
  }, [session_id])

  const handleBackToPractice = () => {
    navigate('/practice')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">正在加载评价报告...</p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || '报告不存在'}</p>
          <button
            onClick={handleBackToPractice}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            返回练习
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">对练评价报告</h1>
          <p className="text-gray-600">基于SPIN方法论的专业反馈</p>
        </div>

        {/* 总体评分 */}
        <div className="bg-white rounded-2xl shadow-sm p-8 mb-6">
          <div className="flex items-center justify-center mb-6">
            <div className="relative">
              <div className="w-32 h-32 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-4xl font-bold text-white">{report.overall_score}</div>
                  <div className="text-sm text-white/80">综合评分</div>
                </div>
              </div>
            </div>
          </div>

          {/* SPIN四项评分 */}
          <div className="space-y-4">
            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">S-现状</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-green-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.spin_scores?.situation_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.spin_scores?.situation_score || 0}/10</span>
            </div>

            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">P-痛点</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-blue-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.spin_scores?.problem_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.spin_scores?.problem_score || 0}/10</span>
            </div>

            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">I-影响</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-yellow-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.spin_scores?.implication_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.spin_scores?.implication_score || 0}/10</span>
            </div>

            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">N-价值</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-purple-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.spin_scores?.need_payoff_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.spin_scores?.need_payoff_score || 0}/10</span>
            </div>
          </div>
        </div>

        {/* 优点与改进 */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* 优点 */}
          <div className="bg-white rounded-2xl shadow-sm p-6">
            <h3 className="text-lg font-semibold text-green-600 mb-4 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              做得好
            </h3>
            <ul className="space-y-2">
              {report.key_strengths?.map((strength, index) => (
                <li key={index} className="flex items-start">
                  <span className="text-green-500 mr-2">•</span>
                  <span className="text-gray-700">{strength}</span>
                </li>
              )) || <li className="text-gray-500">暂无</li>}
            </ul>
          </div>

          {/* 需改进 */}
          <div className="bg-white rounded-2xl shadow-sm p-6">
            <h3 className="text-lg font-semibold text-orange-600 mb-4 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              需改进
            </h3>
            <ul className="space-y-2">
              {report.areas_for_improvement?.map((area, index) => (
                <li key={index} className="flex items-start">
                  <span className="text-orange-500 mr-2">•</span>
                  <span className="text-gray-700">{area}</span>
                </li>
              )) || <li className="text-gray-500">暂无</li>}
            </ul>
          </div>
        </div>

        {/* 下次练习重点 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-primary mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.003 3.003 0 012.26 2.194l-.28 2.786a1 1 0 001.731 1A1 1 0 0015.8 13.5 3 3 0 0113 16a3.003 3.003 0 01-2.26-2.194l.28-2.786a1 1 0 00-1.731-1A1 1 0 0010 12a1 1 0 00-.867-.5 1 1 0 110-2 1 1 0 00.867-.5 1 1 0 011.731-1A3.003 3.003 0 0113 8a3.003 3.003 0 012.26 2.194l-.28 2.786a1 1 0 001.731 1A1 1 0 0015.8 13.5 3 3 0 0113 16a3.003 3.003 0 01-2.26-2.194l.28-2.786a1 1 0 00-1.731-1A1 1 0 0010 12a1 1 0 00-.867-.5 1 1 0 110-2 1 1 0 00.867-.5 1 1 0 011.731 1A3.003 3.003 0 0113 8a3.003 3.003 0 01-2.26-2.194l.28-2.786a1 1 0 00-1.731-1A1 1 0 0010 12a1 1 0 00-.867.5 1 1 0 110-2 1 1 0 00.867-.5 1 1 0 011.731 1A3.003 3.003 0 0113 8a3.003 3.003 0 012.26 2.194l-.28 2.786a1 1 0 001.731 1A1 1 0 0015.8 13.5 3 3 0 0113 16a3.003 3.003 0 01-2.26-2.194l.28-2.786a1 1 0 00-1.731-1A1 1 0 0010 12a1 1 0 00-.867-.5 1 1 0 110-2 1 1 0 00.867-.5z" clipRule="evenodd" />
            </svg>
            下次练习重点
          </h3>
          <p className="text-gray-700 leading-relaxed">
            {report.next_practice_focus || '继续练习，提升SPIN技能'}
          </p>
        </div>

        {/* 操作按钮 */}
        <div className="flex justify-center gap-4">
          <button
            onClick={handleBackToPractice}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium"
          >
            返回继续练习
          </button>
        </div>
      </div>
    </div>
  )
}