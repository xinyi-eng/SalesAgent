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

interface KnowledgeRef {
  category?: string
  source?: string
  chapter?: string
  section?: string
  excerpt?: string
  relevance?: number
}

/**
 * 单维度的 LLM 评价字段：销售说了什么 / 评分原因 / KB 引用 / 改进建议
 */
interface StageDetail {
  quote?: string       // 销售员实际说的原话
  analysis?: string    // 评分原因
  reference?: string   // 知识库引用
  suggestion?: string  // 改进建议
}

interface ReportData {
  session_id: string
  overall_score: number
  situation_score: number
  problem_score: number
  implication_score: number
  need_payoff_score: number
  // 4 维度 × 4 字段（来自 LLM 真实输出）
  situation?: StageDetail
  problem?: StageDetail
  implication?: StageDetail
  need_payoff?: StageDetail
  // 综合反馈
  key_strengths: string[]
  areas_for_improvement: string[]
  next_practice_focus: string
  knowledge_refs?: KnowledgeRef[]
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

  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const handleDownloadPdf = async () => {
    if (!session_id) return
    setDownloadingPdf(true)
    try {
      await api.downloadReportPdf(session_id)
    } catch (err) {
      console.error('PDF download failed:', err)
      alert('PDF 下载失败，请稍后重试')
    } finally {
      setDownloadingPdf(false)
    }
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
                  style={{ width: `${(report.situation_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.situation_score || 0}/10</span>
            </div>

            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">P-痛点</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-blue-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.problem_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.problem_score || 0}/10</span>
            </div>

            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">I-影响</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-yellow-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.implication_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.implication_score || 0}/10</span>
            </div>

            <div className="flex items-center">
              <span className="w-24 text-gray-700 font-medium">N-价值</span>
              <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                <div
                  className="bg-purple-500 h-4 rounded-full transition-all"
                  style={{ width: `${(report.need_payoff_score || 0) * 10}%` }}
                />
              </div>
              <span className="w-16 text-right text-gray-600">{report.need_payoff_score || 0}/10</span>
            </div>
          </div>
        </div>

        {/* SPIN 4 维度详细评价（来自 LLM 真实输出） */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📋 SPIN 四维详细评价</h3>
          <div className="space-y-4">
            {[
              { key: 'situation', label: 'S-现状探询', color: 'green',
                desc: '询问客户当前背景、规模、痛点' },
              { key: 'problem', label: 'P-难点发掘', color: 'blue',
                desc: '挖出客户具体的不满和困难' },
              { key: 'implication', label: 'I-暗示后果', color: 'yellow',
                desc: '放大问题的影响和代价' },
              { key: 'need_payoff', label: 'N-价值呈现', color: 'purple',
                desc: '让客户自己说解决后的价值' },
            ].map((stage) => {
              const detail = (report as any)[stage.key] as StageDetail | undefined
              if (!detail) return null
              return (
                <details
                  key={stage.key}
                  className="border border-gray-200 rounded-lg p-4 group"
                >
                  <summary className="cursor-pointer list-none flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full bg-${stage.color}-500`} />
                      <span className="font-medium text-gray-800">{stage.label}</span>
                      <span className="text-xs text-gray-500">- {stage.desc}</span>
                    </div>
                    <span className="text-xs text-gray-400 group-open:rotate-180 transition-transform">▼</span>
                  </summary>
                  <div className="mt-3 space-y-2 text-sm">
                    {detail.quote && (
                      <div className="bg-blue-50 border-l-2 border-blue-400 p-2">
                        <div className="text-xs text-blue-600 font-medium mb-1">📌 销售员原话</div>
                        <div className="text-gray-700 italic">"{detail.quote}"</div>
                      </div>
                    )}
                    {detail.analysis && (
                      <div>
                        <div className="text-xs text-gray-500 font-medium">💡 评分原因</div>
                        <div className="text-gray-700">{detail.analysis}</div>
                      </div>
                    )}
                    {detail.reference && (
                      <div className="bg-amber-50 border-l-2 border-amber-400 p-2">
                        <div className="text-xs text-amber-700 font-medium mb-1">📚 知识库依据</div>
                        <div className="text-gray-700">{detail.reference}</div>
                      </div>
                    )}
                    {detail.suggestion && (
                      <div className="bg-green-50 border-l-2 border-green-400 p-2">
                        <div className="text-xs text-green-700 font-medium mb-1">✅ 改进建议</div>
                        <div className="text-gray-700">{detail.suggestion}</div>
                      </div>
                    )}
                  </div>
                </details>
              )
            })}
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

        {/* 知识库引用（RAG）：本场对练中 AI 客户的话术依据 */}
        {report.knowledge_refs && report.knowledge_refs.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
            <h3 className="text-lg font-semibold text-secondary mb-4 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.186 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              AI 客户的话术依据 ({report.knowledge_refs.length} 条)
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              以下是本场对练中 AI 客户引用的销售知识库条目（依据相关度排序）
            </p>
            <div className="space-y-3">
              {report.knowledge_refs.map((ref, idx) => (
                <div
                  key={idx}
                  className="border border-secondary/20 rounded-lg p-4 bg-secondary/5"
                >
                  <div className="flex items-start gap-3">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-secondary text-white text-xs font-medium flex-shrink-0">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-800">
                        {ref.source || '知识库'}
                        {ref.chapter ? ` · ${ref.chapter}` : ''}
                        {ref.section ? ` · ${ref.section}` : ''}
                      </div>
                      {ref.category && (
                        <div className="mt-1 text-xs text-gray-500">
                          分类: {ref.category}
                          {ref.relevance != null && ` · 相关度 ${(ref.relevance * 100).toFixed(0)}%`}
                        </div>
                      )}
                      {ref.excerpt && (
                        <div className="mt-2 text-sm text-gray-700 leading-relaxed">
                          {ref.excerpt}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex justify-center gap-4 flex-wrap">
          <button
            onClick={handleBackToPractice}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium"
          >
            返回继续练习
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="px-6 py-3 bg-secondary text-white rounded-xl hover:bg-secondary/90 transition-colors font-medium flex items-center gap-2 disabled:opacity-60"
          >
            {downloadingPdf ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                  <path fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                正在生成 PDF...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                导出 PDF
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}