/**
 * SpinStageHint Component - Real-time SPIN stage guidance
 * OR-4: 实时SPIN阶段提示
 * Shows current stage, description, and suggested questions
 */

interface SpinStageHintProps {
  phase: 'opening' | 'discovery' | 'needs' | 'proposal' | 'closing'
  className?: string
}

const SPIN_STAGES = {
  opening: {
    label: '开场破冰',
    spin: 'S',
    color: 'bg-blue-100 text-blue-700 border-blue-200',
    description: '建立亲和感，快速了解客户基本信息',
    tips: [
      '简单问候，不要直接谈产品',
      '了解客户职位和公司背景',
      '观察客户沟通风格'
    ],
    exampleQuestions: [
      '您公司目前销售团队规模多大？',
      '主要通过什么渠道获客？'
    ]
  },
  discovery: {
    label: '需求挖掘',
    spin: 'S-P',
    color: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    description: '发现客户面临的问题和困难（背景问题 + 难点问题）',
    tips: [
      '用开放式问题探查客户痛点',
      '不要问过多背景问题，快速转入难点',
      '倾听客户的不满和困扰'
    ],
    exampleQuestions: [
      '销售过程中遇到最多的问题是什么？',
      '您对目前的供应商有哪些不满意的地方？'
    ]
  },
  needs: {
    label: '方案呈现',
    spin: 'I',
    color: 'bg-orange-100 text-orange-700 border-orange-200',
    description: '放大问题的后果，让客户感受到紧迫性（暗示问题）',
    tips: [
      '追问问题不解决的后果',
      '让客户自己说出问题的严重性',
      '避免直接批评或施压'
    ],
    exampleQuestions: [
      '这个问题对您的业务有什么影响？',
      '如果持续下去，会造成什么后果？'
    ]
  },
  proposal: {
    label: '促成成交',
    spin: 'N',
    color: 'bg-green-100 text-green-700 border-green-200',
    description: '引导客户自己说出方案价值（需求效益问题）',
    tips: [
      '问：如果能解决这个问题，对您有什么价值？',
      '让客户自己说出方案的优势',
      '避免直接推销，让客户自己结论'
    ],
    exampleQuestions: [
      '如果效率能提高30%，您觉得会带来什么价值？',
      '您觉得什么样的结果才值得投入？'
    ]
  },
  closing: {
    label: '复盘总结',
    spin: '-',
    color: 'bg-gray-100 text-gray-700 border-gray-200',
    description: '总结对话，确认下一步行动',
    tips: [
      '回顾客户认可的问题和价值',
      '确认客户决策流程',
      '约定下次见面或演示时间'
    ],
    exampleQuestions: [
      '您看我们是先做试点还是直接全面部署？',
      '还有什么问题需要我解答吗？'
    ]
  }
}

export default function SpinStageHint({ phase, className = '' }: SpinStageHintProps) {
  const stage = SPIN_STAGES[phase] || SPIN_STAGES.opening

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {/* Current Stage Badge */}
      <div className={`px-3 py-2 rounded-lg border ${stage.color}`}>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold">{stage.spin}</span>
          <div>
            <p className="font-semibold text-sm">{stage.label}</p>
            <p className="text-xs opacity-80">{stage.description}</p>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <p className="text-xs font-medium text-gray-500 mb-2">销售提示</p>
        <ul className="space-y-1">
          {stage.tips.map((tip, i) => (
            <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
              <span className="text-primary font-bold">•</span>
              {tip}
            </li>
          ))}
        </ul>
      </div>

      {/* Example Questions */}
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <p className="text-xs font-medium text-gray-500 mb-2">参考问题</p>
        <ul className="space-y-2">
          {stage.exampleQuestions.map((q, i) => (
            <li key={i} className="text-xs text-gray-700 bg-gray-50 px-2 py-1.5 rounded">
              &quot;{q}&quot;
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}