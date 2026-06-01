/**
 * RoleSelector Component
 *
 * Three-dimensional role configuration selector:
 * - Position Level (岗位级别): 初级的客户经理 / 中级的采购经理 / 高级的总监
 * - Personality (性格): 理性型 / 感性型 / 犹豫型 / 果断型
 * - Decision Style (决策风格): 价格导向 / 价值导向 / 关系导向 / 风险规避
 *
 * States: default / selected / disabled
 */
import { RoleConfig } from '../../api/practice'

interface RoleSelectorProps {
  selectedConfig: RoleConfig | null
  onChange: (config: RoleConfig) => void
  isDisabled?: boolean
}

const positionLevels = [
  { value: 'junior', label: '初级的客户经理', description: '刚入职1-2年，预算有限' },
  { value: 'middle', label: '中级的采购经理', description: '负责部门采购，有一定决策权' },
  { value: 'senior', label: '高级的总监', description: '部门负责人，预算充足但更谨慎' }
]

const personalities = [
  { value: 'rational', label: '理性型', description: '注重数据和分析，决策慢' },
  { value: 'emotional', label: '感性型', description: '重视感觉和关系，容易被打动' },
  { value: 'hesitant', label: '犹豫型', description: '反复比较，迟迟不做决定' },
  { value: 'decisive', label: '果断型', description: '快速决策，但可能冲动' }
]

const decisionStyles = [
  { value: 'price_oriented', label: '价格导向', description: '最关心价格，追求性价比' },
  { value: 'value_oriented', label: '价值导向', description: '关注长期价值和ROI' },
  { value: 'relationship_oriented', label: '关系导向', description: '重视信任和长期合作关系' },
  { value: 'risk_averse', label: '风险规避', description: '关注潜在风险，决策保守' }
]

const RoleSelector = ({ selectedConfig, onChange, isDisabled = false }: RoleSelectorProps) => {
  const isOptionSelected = (category: keyof RoleConfig, value: string) => {
    return selectedConfig?.[category] === value
  }

  const handleSelect = (category: keyof RoleConfig, value: string) => {
    if (isDisabled) return
    onChange({
      ...(selectedConfig || { position_level: '', personality: '', decision_style: '' }),
      [category]: value
    } as RoleConfig)
  }

  const renderOptions = (
    items: Array<{ value: string; label: string; description: string }>,
    category: keyof RoleConfig
  ) => (
    <div className="grid grid-cols-2 gap-3">
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => handleSelect(category, item.value)}
          disabled={isDisabled}
          className={`
            p-3 rounded-lg border-2 text-left transition-all duration-200
            ${isOptionSelected(category, item.value)
              ? 'border-primary bg-blue-50'
              : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
            }
            ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <div className="font-medium text-gray-900">{item.label}</div>
          <div className="text-xs text-gray-500 mt-1">{item.description}</div>
        </button>
      ))}
    </div>
  )

  const isComplete = selectedConfig?.position_level && selectedConfig?.personality && selectedConfig?.decision_style

  return (
    <div className="space-y-6">
      {/* Position Level */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          岗位级别 <span className="text-red-500">*</span>
        </label>
        {renderOptions(positionLevels, 'position_level')}
      </div>

      {/* Personality */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          客户性格 <span className="text-red-500">*</span>
        </label>
        {renderOptions(personalities, 'personality')}
      </div>

      {/* Decision Style */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          决策风格 <span className="text-red-500">*</span>
        </label>
        {renderOptions(decisionStyles, 'decision_style')}
      </div>

      {/* Preview */}
      {isComplete && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-2">角色预览</h4>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary/10 text-primary">
              {positionLevels.find(p => p.value === selectedConfig?.position_level)?.label}
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-secondary/10 text-secondary">
              {personalities.find(p => p.value === selectedConfig?.personality)?.label}
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-success/10 text-success">
              {decisionStyles.find(d => d.value === selectedConfig?.decision_style)?.label}
            </span>
          </div>
        </div>
      )}

      {/* Status */}
      {!isComplete && (
        <p className="text-sm text-gray-500 text-center">
          请完成所有选择以配置AI客户角色
        </p>
      )}
    </div>
  )
}

export default RoleSelector
