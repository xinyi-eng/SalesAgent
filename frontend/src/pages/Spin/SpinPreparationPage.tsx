/**
 * SpinPreparationPage - SPIN访前准备页面（增强版）
 *
 * 功能流程：
 * 1. 输入客户名称 → AI自动调查
 * 2. 确认/补充客户背景信息
 * 3. 确认痛点
 * 4. 生成SPIN问题清单
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSpinStore } from '../../stores/spinStore'
import type { CompanyInfo, PersonInfo } from '../../api/spin'

// 行业选项
const INDUSTRIES = [
  '制造业', '医疗健康', '教育培训', '零售电商', '金融服务',
  '科技软件', '建筑工程', '物流运输', '能源化工', '其他'
]

// 规模选项
const SCALES = [
  '微小企业（<50人）',
  '中小企业（50-200人）',
  '中大型企业（200-1000人）',
  '大型企业（>1000人）'
]

// 痛点选项
const PAIN_POINTS = [
  '成本压力高',
  '效率低下',
  '人才流失',
  '客户流失',
  '竞争激烈',
  '技术落后',
  '管理困难',
  '资金紧张'
]

const SpinPreparationPage = () => {
  const navigate = useNavigate()
  const {
    currentStep,
    setCurrentStep,
    customerName,
    setCustomerName,
    customerContext,
    setCustomerContext,
    isInvestigating,
    investigationResult,
    investigateError,
    investigate,
    confirmedPains,
    togglePain,
    questionList,
    generateQuestions
  } = useSpinStore()

  const [showExtraInfo, setShowExtraInfo] = useState(false)

  const handleInvestigate = () => {
    if (customerName.trim()) {
      investigate(customerName)
    }
  }

  const handleConfirmInfo = () => {
    setCurrentStep('pain_points')
  }

  const handleConfirmPains = async () => {
    // First, persist pain points to customerContext so SPIN generator can use them
    if (customerContext) {
      setCustomerContext({
        ...customerContext,
        pain_points: confirmedPains
      })
    }
    setCurrentStep('questions')  // show loading state
    await generateQuestions()
  }

  const handleStartPractice = () => {
    if (questionList && customerContext) {
      setCustomerContext(customerContext)
      navigate('/practice', {
        state: {
          spinQuestionListId: questionList.question_list_id,
          customerContext: customerContext,
          investigationResult: investigationResult
        }
      })
    }
  }

  // Helper to safely render unknown values in JSX
  const safeRender = (val: unknown): string => {
    if (val == null) return ''
    if (Array.isArray(val)) return val.join('；')
    return String(val)
  }

  // Get all questions from questionList as a flat array with stage info
  const getAllQuestions = () => {
    if (!questionList) return []
    const questions: Array<{ stage: string; text: string; target?: string; guidance?: string }> = []

    if (questionList.situation_questions) {
      questionList.situation_questions.forEach((q: string) => {
        questions.push({ stage: 'situation', text: q, target: '了解现状' })
      })
    }
    if (questionList.problem_questions) {
      questionList.problem_questions.forEach((q: string) => {
        questions.push({ stage: 'problem', text: q, target: '挖掘痛点' })
      })
    }
    if (questionList.implication_questions) {
      questionList.implication_questions.forEach((q: string) => {
        questions.push({ stage: 'implication', text: q, target: '扩大影响' })
      })
    }
    if (questionList.need_payoff_questions) {
      questionList.need_payoff_questions.forEach((q: string) => {
        questions.push({ stage: 'need_payoff', text: q, target: '价值呈现' })
      })
    }
    return questions
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">SPIN访前准备</h1>
          <p className="text-gray-600 mt-2">AI智能调研客户，开启个性化销售对练</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8">
          {['info', 'investigation', 'pain_points', 'questions'].map((step, index) => (
            <div key={step} className="flex items-center">
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                ${currentStep === step ? 'bg-primary text-white' :
                  ['info', 'investigation', 'pain_points', 'questions'].indexOf(currentStep) > index
                    ? 'bg-success text-white' : 'bg-gray-200 text-gray-600'}
              `}>
                {index + 1}
              </div>
              {index < 3 && <div className="w-16 h-1 bg-gray-200 mx-2" />}
            </div>
          ))}
        </div>

        {/* Step 1: Customer Info */}
        {currentStep === 'info' && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">输入客户信息</h2>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                客户名称
              </label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="请输入公司或个人名称"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
            </div>

            {customerContext && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900 mb-3">基本信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-500">行业</span>
                    <p className="font-medium">{customerContext.industry || '未选择'}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">规模</span>
                    <p className="font-medium">{customerContext.scale || '未选择'}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={handleInvestigate}
                disabled={!customerName.trim() || isInvestigating}
                className="flex-1 px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isInvestigating ? '调研中...' : 'AI智能调研'}
              </button>
              {customerContext && (
                <button
                  onClick={handleConfirmInfo}
                  className="px-6 py-3 bg-success text-white rounded-lg hover:bg-success/90 font-medium"
                >
                  确认信息
                </button>
              )}
            </div>

            {investigateError && (
              <p className="mt-4 text-sm text-red-600">{investigateError}</p>
            )}
          </div>
        )}

        {/* Step 2: Investigation Results */}
        {currentStep === 'investigation' && investigationResult && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">调研结果确认</h2>

            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">
                  {investigationResult.subject_type === 'company'
                    ? (investigationResult as CompanyInfo).background?.slice(0, 100) + '...'
                    : `${(investigationResult as PersonInfo).name} - ${(investigationResult as PersonInfo).title}`}
                </h3>
                <button
                  onClick={() => setShowExtraInfo(!showExtraInfo)}
                  className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  {showExtraInfo ? '▼' : '▶'} 点击查看更多调查资料
                </button>
              </div>

              {showExtraInfo && (
                <div className="mt-3 p-4 bg-white rounded-lg text-sm space-y-2">
                  {!!investigationResult.extra_info.media_reports && Array.isArray(investigationResult.extra_info.media_reports) && (
                    <div>
                      <span className="font-medium text-gray-700">媒体报道：</span>
                      {(investigationResult.extra_info.media_reports as string[]).join('；')}
                    </div>
                  )}
                  {!!investigationResult.extra_info.funding_status && (
                    <div>
                      <span className="font-medium text-gray-700">融资情况：</span>
                      <span>{safeRender(investigationResult.extra_info.funding_status)}</span>
                    </div>
                  )}
                  {!!investigationResult.extra_info.leader_info && (
                    <div>
                      <span className="font-medium text-gray-700">高管信息：</span>
                      <span>{safeRender(investigationResult.extra_info.leader_info)}</span>
                    </div>
                  )}
                  {!!investigationResult.extra_info.expertise && (
                    <div>
                      <span className="font-medium text-gray-700">擅长领域：</span>
                      <span>{safeRender(investigationResult.extra_info.expertise)}</span>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <span className="text-sm text-gray-500">近期动态</span>
                  <ul className="mt-1 space-y-1">
                    {(investigationResult as PersonInfo).recent_activities?.slice(0, 3).map((activity, i) => (
                      <li key={i} className="text-sm text-gray-700">• {activity}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <span className="text-sm text-gray-500">潜在痛点</span>
                  <ul className="mt-1 space-y-1">
                    {investigationResult.potential_pains?.slice(0, 3).map((pain, i) => (
                      <li key={i} className="text-sm text-gray-700">• {pain}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* 客户背景选择 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">行业</label>
              <select
                value={customerContext?.industry || ''}
                onChange={(e) => setCustomerContext({ ...customerContext!, industry: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">请选择行业</option>
                {INDUSTRIES.map(ind => (
                  <option key={ind} value={ind}>{ind}</option>
                ))}
              </select>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">规模</label>
              <select
                value={customerContext?.scale || ''}
                onChange={(e) => setCustomerContext({ ...customerContext!, scale: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">请选择规模</option>
                {SCALES.map(scale => (
                  <option key={scale} value={scale}>{scale}</option>
                ))}
              </select>
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep('info')}
                className="px-6 py-3 text-gray-600 hover:text-gray-800"
              >
                上一步
              </button>
              <button
                onClick={handleConfirmInfo}
                disabled={!customerContext?.industry || !customerContext?.scale}
                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                确认并继续
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Pain Points */}
        {currentStep === 'pain_points' && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">确认客户痛点</h2>

            <div className="grid grid-cols-2 gap-3 mb-6">
              {PAIN_POINTS.map(pain => (
                <button
                  key={pain}
                  onClick={() => togglePain(pain)}
                  className={`
                    p-4 rounded-lg border-2 text-left transition-all
                    ${confirmedPains.includes(pain)
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  {pain}
                </button>
              ))}
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep('investigation')}
                className="px-6 py-3 text-gray-600 hover:text-gray-800"
              >
                上一步
              </button>
              <button
                onClick={handleConfirmPains}
                disabled={confirmedPains.length === 0}
                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                确认痛点并生成问题
              </button>
            </div>
          </div>
        )}

        {/* Step 4: SPIN Questions */}
        {currentStep === 'questions' && questionList && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">SPIN问题清单</h2>

            <div className="space-y-4">
              {getAllQuestions().map((q, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-start gap-3">
                    <span className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0
                      ${q.stage === 'situation' ? 'bg-blue-100 text-blue-700' :
                        q.stage === 'problem' ? 'bg-yellow-100 text-yellow-700' :
                        q.stage === 'implication' ? 'bg-orange-100 text-orange-700' :
                        'bg-green-100 text-green-700'}
                    `}>
                      {q.stage[0].toUpperCase()}
                    </span>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 mb-1">{q.text}</p>
                      <p className="text-sm text-gray-500">
                        目标：{q.target || '挖掘客户需求'}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-between mt-6">
              <button
                onClick={() => setCurrentStep('pain_points')}
                className="px-6 py-3 text-gray-600 hover:text-gray-800"
              >
                上一步
              </button>
              <button
                onClick={handleStartPractice}
                className="px-6 py-3 bg-success text-white rounded-lg hover:bg-success/90 font-medium"
              >
                开始对练
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SpinPreparationPage
