/**
 * ScenarioCard Component
 *
 * Displays a practice scenario with icon, title, description, and tags
 *
 * States: default / hover(轻微上浮) / selected(边框高亮) / disabled
 * Size: card width adaptive, spacing 16px
 */
import { Scenario } from '@/api/practice'

interface ScenarioCardProps {
  scenario: Scenario
  isSelected: boolean
  isDisabled?: boolean
  onClick: () => void
}

// Scenario type to icon mapping
const scenarioIcons: Record<string, string> = {
  '初次拜访': '👋',
  '产品讲解': '📦',
  '价格谈判': '💰',
  '竞品对比': '⚔️',
  '异议处理': '🛡️',
  '促成成交': '🤝',
  '售后维护': '🔧'
}

const ScenarioCard = ({ scenario, isSelected, isDisabled = false, onClick }: ScenarioCardProps) => {
  const icon = scenarioIcons[scenario.type] || '📋'

  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className={`
        w-full text-left p-4 rounded-lg border-2 transition-all duration-200
        ${isSelected
          ? 'border-primary bg-blue-50 shadow-md'
          : 'border-gray-200 bg-surface hover:shadow-md hover:-translate-y-0.5'
        }
        ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      style={{
        width: '100%',
        minHeight: '120px'
      }}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="text-3xl flex-shrink-0" aria-hidden="true">
          {icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {scenario.name}
          </h3>

          {/* Description */}
          {scenario.description && (
            <p className="text-sm text-gray-600 line-clamp-2 mb-2">
              {scenario.description}
            </p>
          )}

          {/* Tags */}
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary">
              {scenario.type}
            </span>
            {scenario.category && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                {scenario.category}
              </span>
            )}
            {scenario.is_builtin && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success/10 text-success">
                内置
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}

export default ScenarioCard