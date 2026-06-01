/**
 * SpinPreparationPage - SPIN访前准备页面
 *
 * 用户填写客户背景，AI生成个性化SPIN问题清单
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSpinStore } from '../../stores/spinStore'
import { CustomerContext } from '../../api/spin'

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

// 预设痛点选项
const PAIN_POINT_OPTIONS = [
  '销售团队能力不足',
  '客户转化率低',
  '销售周期过长',
  '竞争压力大',
  '客户流失率高',
  '产品知识掌握不够',
  '销售话术不专业',
  '不懂SPIN提问',
  '异议处理困难',
  '不知道如何缔结'
]

const SpinPreparationPage = () => {
  const navigate = useNavigate()
  const {
    customerContext,
    setCustomerContext,
    questionList,
    isGenerating,
    error,
    generateQuestions,
    clearQuestions
  } = useSpinStore()

  const [industry, setIndustry] = useState('')
  const [scale, setScale] = useState('')
  const [customPainPoints, setCustomPainPoints] = useState<string[]>([])
  const [customPainInput, setCustomPainInput] = useState('')

  const handlePainPointToggle = (point: string) => {
    setCustomPainPoints(prev =>
      prev.includes(point)
        ? prev.filter(p => p !== point)
        : [...prev, point]
    )
  }

  const handleAddCustomPain = () => {
    if (customPainInput.trim() && !customPainPoints.includes(customPainInput.trim())) {
      setCustomPainPoints(prev => [...prev, customPainInput.trim()])
      setCustomPainInput('')
    }
  }

  const handleGenerate = () => {
    if (!industry) {
      alert('请选择行业')
      return
    }
    if (!scale) {
      alert('请选择客户规模')
      return
    }
    if (customPainPoints.length === 0) {
      alert('请至少选择一个痛点')
      return
    }

    const context: CustomerContext = {
      industry,
      scale,
      pain_points: customPainPoints
    }
    setCustomerContext(context)
    generateQuestions()
  }

  const handleStartPractice = () => {
    if (questionList) {
      // 将问题清单ID传递到practice store
      navigate('/practice', { state: { spinQuestionListId: questionList.question_list_id } })
    }
  }

  const handleReset = () => {
    setIndustry('')
    setScale('')
    setCustomPainPoints([])
    setCustomPainInput('')
    clearQuestions()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            SPIN访前准备
          </h1>
          <p className="text-gray-600">
            填写客户背景，AI将为您生成个性化的SPIN提问清单，帮助您做好拜访准备
          </p>
        </div>

        {!questionList ? (
          /* 客户背景输入表单 */
          <div className="bg-white rounded-xl shadow-sm p-6">
            {/* 行业选择 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                客户行业 <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {INDUSTRIES.map(ind => (
                  <button
                    key={ind}
                    onClick={() => setIndustry(ind)}
                    className={`px-4 py-2 rounded-lg text-sm transition-all ${
                      industry === ind
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {ind}
                  </button>
                ))}
              </div>
            </div>

            {/* 规模选择 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                客户规模 <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {SCALES.map(s => (
                  <button
                    key={s}
                    onClick={() => setScale(s)}
                    className={`px-4 py-3 rounded-lg text-sm text-left transition-all ${
                      scale === s
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* 痛点选择 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                客户痛点 <span className="text-red-500">*</span>（可多选）
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {PAIN_POINT_OPTIONS.map(point => (
                  <button
                    key={point}
                    onClick={() => handlePainPointToggle(point)}
                    className={`px-3 py-1.5 rounded-full text-sm transition-all ${
                      customPainPoints.includes(point)
                        ? 'bg-secondary text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {point}
                  </button>
                ))}
              </div>
              {/* 自定义痛点输入 */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customPainInput}
                  onChange={(e) => setCustomPainInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCustomPain())}
                  placeholder="输入自定义痛点后按回车添加"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <button
                  onClick={handleAddCustomPain}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  添加
                </button>
              </div>
              {/* 已选痛点 */}
              {customPainPoints.length > 0 && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500 mb-2">已选择：</p>
                  <div className="flex flex-wrap gap-2">
                    {customPainPoints.map(p => (
                      <span
                        key={p}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-white border border-gray-200 rounded-full text-sm"
                      >
                        {p}
                        <button
                          onClick={() => handlePainPointToggle(p)}
                          className="text-gray-400 hover:text-red-500"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* 生成按钮 */}
            <div className="flex gap-3">
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !industry || !scale || customPainPoints.length === 0}
                className={`flex-1 py-3 rounded-lg font-medium transition-all ${
                  isGenerating
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-primary text-white hover:bg-primary/90'
                }`}
              >
                {isGenerating ? '生成中...' : '生成SPIN问题清单'}
              </button>
              <button
                onClick={handleReset}
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                重置
              </button>
            </div>

            {error && (
              <p className="mt-3 text-sm text-red-500">{error}</p>
            )}
          </div>
        ) : (
          /* 问题清单展示 */
          <div className="space-y-6">
            {/* 问题清单卡片 */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">SPIN问题清单</h2>
                <span className="text-sm text-gray-500">
                  生成时间：{new Date(questionList.created_at).toLocaleString()}
                </span>
              </div>

              {/* 客户背景摘要 */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-2">客户背景</p>
                <div className="flex flex-wrap gap-4 text-sm">
                  <span className="px-3 py-1 bg-white rounded-full border">
                    行业：{questionList.customer_context.industry}
                  </span>
                  <span className="px-3 py-1 bg-white rounded-full border">
                    规模：{questionList.customer_context.scale}
                  </span>
                  <span className="px-3 py-1 bg-white rounded-full border">
                    痛点：{questionList.customer_context.pain_points.length}个
                  </span>
                </div>
              </div>

              {/* 四类问题 */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Situation */}
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h3 className="font-bold text-blue-700 mb-2">
                    S - 现状问题（了解背景）
                  </h3>
                  <ul className="space-y-2">
                    {questionList.situation_questions.map((q, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-700">
                        <span className="text-blue-500 font-medium">{i + 1}.</span>
                        {q}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Problem */}
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h3 className="font-bold text-purple-700 mb-2">
                    P - 难点问题（发现痛点）
                  </h3>
                  <ul className="space-y-2">
                    {questionList.problem_questions.map((q, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-700">
                        <span className="text-purple-500 font-medium">{i + 1}.</span>
                        {q}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Implication */}
                <div className="p-4 bg-orange-50 rounded-lg">
                  <h3 className="font-bold text-orange-700 mb-2">
                    I - 暗示问题（放大影响）
                  </h3>
                  <ul className="space-y-2">
                    {questionList.implication_questions.map((q, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-700">
                        <span className="text-orange-500 font-medium">{i + 1}.</span>
                        {q}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Need-payoff */}
                <div className="p-4 bg-green-50 rounded-lg">
                  <h3 className="font-bold text-green-700 mb-2">
                    N - 需求效益问题（引导价值）
                  </h3>
                  <ul className="space-y-2">
                    {questionList.need_payoff_questions.map((q, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-700">
                        <span className="text-green-500 font-medium">{i + 1}.</span>
                        {q}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-3">
              <button
                onClick={handleStartPractice}
                className="flex-1 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90"
              >
                开始模拟销售
              </button>
              <button
                onClick={handleReset}
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                重新生成
              </button>
            </div>
          </div>
        )}

        {/* 提示信息 */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-700 mb-2">使用提示</h4>
          <ul className="text-sm text-blue-600 space-y-1">
            <li>• 提前生成SPIN问题清单，做好拜访准备</li>
            <li>• 在模拟销售时，AI会根据这些背景信息扮演客户</li>
            <li>• 建议结合问题清单进行针对性的练习</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default SpinPreparationPage
