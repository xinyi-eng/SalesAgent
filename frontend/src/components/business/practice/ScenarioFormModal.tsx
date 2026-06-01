/**
 * ScenarioFormModal Component - Create/Edit scenario modal
 */
import { useState } from 'react'
import { Scenario } from '../../api/practice'

interface ScenarioFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: ScenarioFormData) => Promise<void>
  scenario?: Scenario | null
  mode: 'create' | 'edit'
}

export interface ScenarioFormData {
  name: string
  description: string
  type: string
  category: string
  sub_category: string
}

const INITIAL_DATA: ScenarioFormData = {
  name: '',
  description: '',
  type: 'cold_call',
  category: 'enterprise_software',
  sub_category: 'crm'
}

const SCENARIO_TYPES = [
  { value: 'cold_call', label: '陌拜电话' },
  { value: 'online_meeting', label: '线上会议' },
  { value: 'factory_visit', label: '工厂参观' },
  { value: 'business_dinner', label: '商务宴请' }
]

const CATEGORIES = [
  { value: 'enterprise_software', label: '企业软件' },
  { value: 'manufacturing', label: '制造业' },
  { value: 'consulting', label: '咨询业' },
  { value: 'service', label: '服务业' }
]

const SUB_CATEGORIES: Record<string, Array<{ value: string; label: string }>> = {
  enterprise_software: [
    { value: 'crm', label: 'CRM系统' },
    { value: 'erp', label: 'ERP系统' },
    { value: 'oa', label: 'OA系统' },
    { value: 'data_analytics', label: '数据分析' }
  ],
  manufacturing: [
    { value: 'machinery', label: '机械设备' },
    { value: 'electronics', label: '电子设备' },
    { value: 'chemical', label: '化工原料' },
    { value: 'automotive', label: '汽车配件' }
  ],
  consulting: [
    { value: 'management', label: '管理咨询' },
    { value: 'digital', label: '数字化咨询' },
    { value: 'hr', label: '人力资源咨询' }
  ],
  service: [
    { value: 'it_outsourcing', label: 'IT外包' },
    { value: 'training', label: '企业培训' },
    { value: 'legal', label: '法律服务' }
  ]
}

const ScenarioFormModal = ({ isOpen, onClose, onSubmit, scenario, mode }: ScenarioFormModalProps) => {
  const [formData, setFormData] = useState<ScenarioFormData>(
    scenario
      ? {
          name: scenario.name,
          description: scenario.description || '',
          type: scenario.type,
          category: scenario.category || '',
          sub_category: scenario.sub_category || ''
        }
      : INITIAL_DATA
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      await onSubmit(formData)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              {mode === 'create' ? '创建新场景' : '编辑场景'}
            </h3>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  场景名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：CRM系统需求挖掘"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  场景描述
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="描述这个场景的背景和目标..."
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  场景类型 <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                >
                  {SCENARIO_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    行业分类
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value, sub_category: '' })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    <option value="">请选择</option>
                    {CATEGORIES.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    产品线
                  </label>
                  <select
                    value={formData.sub_category}
                    onChange={(e) => setFormData({ ...formData, sub_category: e.target.value })}
                    disabled={!formData.category}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="">请选择</option>
                    {formData.category && SUB_CATEGORIES[formData.category]?.map((sub) => (
                      <option key={sub.value} value={sub.value}>
                        {sub.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !formData.name}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? '提交中...' : mode === 'create' ? '创建场景' : '保存修改'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ScenarioFormModal