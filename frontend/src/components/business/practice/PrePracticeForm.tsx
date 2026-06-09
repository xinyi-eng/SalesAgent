/**
 * PrePracticeForm - 对练开始前的"销售员档案"填写表单
 *
 * 收集：
 * 1. 销售员姓名（可预填当前 user.full_name）
 * 2. 职级（初级/中级/高级/经理）
 * 3. 销售年限
 * 4. 本次重点练习（多选 SPIN 阶段 + 关系建立）
 * 5. AI 客户难度（简单/中等/困难）
 * 6. 备注（自由文本，给 LLM 看的）
 */
import { useState } from 'react'

export interface UserContext {
  sales_name: string
  sales_level: string  // 初级销售/中级销售/高级销售/销售经理
  years_experience: number
  practice_goals: string[]  // SPIN 4 阶段 + 关系建立
  difficulty: string  // 简单/中等/困难
  notes: string
}

interface PrePracticeFormProps {
  defaultName?: string
  onSubmit: (ctx: UserContext) => void
  onCancel: () => void
}

const SALES_LEVELS = [
  { value: 'junior', label: '初级销售', desc: '1-2 年经验' },
  { value: 'mid', label: '中级销售', desc: '3-5 年经验' },
  { value: 'senior', label: '高级销售', desc: '5+ 年经验' },
  { value: 'manager', label: '销售经理', desc: '带团队' },
]

const PRACTICE_GOALS = [
  { value: 'opening', label: '开场破冰', emoji: '👋' },
  { value: 'discovery', label: '需求挖掘', emoji: '🔍' },
  { value: 'presentation', label: '产品呈现', emoji: '📦' },
  { value: 'objection', label: '异议处理', emoji: '🛡️' },
  { value: 'closing', label: '促成成交', emoji: '🤝' },
  { value: 'rapport', label: '关系建立', emoji: '💬' },
]

const DIFFICULTIES = [
  { value: 'easy', label: '简单', desc: '客户配合，容易对话' },
  { value: 'medium', label: '中等', desc: '真实场景，适度挑战' },
  { value: 'hard', label: '困难', desc: '刁难客户，逼极限' },
]

const PrePracticeForm = ({ defaultName, onSubmit, onCancel }: PrePracticeFormProps) => {
  const [name, setName] = useState(defaultName || '')
  const [level, setLevel] = useState('mid')
  const [years, setYears] = useState(3)
  const [goals, setGoals] = useState<string[]>(['opening'])
  const [difficulty, setDifficulty] = useState('medium')
  const [notes, setNotes] = useState('')

  const toggleGoal = (g: string) => {
    setGoals(prev => (prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]))
  }

  const handleSubmit = () => {
    if (!name.trim()) {
      alert('请填写你的销售员姓名（让 AI 客户知道怎么称呼）')
      return
    }
    if (goals.length === 0) {
      alert('至少选 1 个本次重点练习的方向')
      return
    }
    onSubmit({
      sales_name: name.trim(),
      sales_level: level,
      years_experience: years,
      practice_goals: goals,
      difficulty,
      notes: notes.trim(),
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">📋 销售员档案</h2>
          <p className="text-sm text-gray-500 mt-1">
            对练开始前告诉 AI 客户：你是谁、想练什么、想要多难。这样 AI 会"看人下菜碟"。
          </p>
        </div>

        <div className="p-6 space-y-5">
          {/* 姓名 */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              你的称呼 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="比如：王销售 / 小张 / 张总"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              AI 客户可能会直接叫你"小张"，不填就会被叫"销售员"
            </p>
          </div>

          {/* 职级 */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              你的职级
            </label>
            <div className="grid grid-cols-2 gap-2">
              {SALES_LEVELS.map((l) => (
                <button
                  key={l.value}
                  type="button"
                  onClick={() => setLevel(l.value)}
                  className={`
                    px-3 py-2 rounded-lg border text-left text-sm transition-colors
                    ${level === l.value
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-gray-200 hover:border-gray-300'}
                  `}
                >
                  <div className="font-medium">{l.label}</div>
                  <div className="text-xs text-gray-500">{l.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 销售年限 */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              销售年限：<span className="text-primary font-semibold">{years} 年</span>
            </label>
            <input
              type="range"
              min="0"
              max="20"
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
              className="w-full"
            />
          </div>

          {/* 本次重点 */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              本次重点练习（多选）
            </label>
            <div className="grid grid-cols-3 gap-2">
              {PRACTICE_GOALS.map((g) => (
                <button
                  key={g.value}
                  type="button"
                  onClick={() => toggleGoal(g.value)}
                  className={`
                    px-3 py-2 rounded-lg border text-sm transition-colors flex items-center gap-1.5
                    ${goals.includes(g.value)
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-gray-200 hover:border-gray-300'}
                  `}
                >
                  <span>{g.emoji}</span>
                  <span>{g.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 难度 */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              AI 客户难度
            </label>
            <div className="grid grid-cols-3 gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDifficulty(d.value)}
                  className={`
                    px-3 py-2 rounded-lg border text-left text-sm transition-colors
                    ${difficulty === d.value
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-gray-200 hover:border-gray-300'}
                  `}
                >
                  <div className="font-medium">{d.label}</div>
                  <div className="text-xs text-gray-500">{d.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 备注 */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              备注（可选，告诉 AI 客户你想让它配合什么场景）
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="比如：'我想让你扮演一个正在比较 3 家供应商的采购经理' 或 '重点测我能不能在 5 句内挖出痛点'"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            返回
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            开始对练
          </button>
        </div>
      </div>
    </div>
  )
}

export default PrePracticeForm
