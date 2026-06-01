/**
 * PracticePage - 场景选择与配置页面
 *
 * Flow:
 * 1. 场景选择 -> 2. 角色配置 -> 3. 开始对练
 *
 * Story: 1.1 场景选择与配置
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePracticeStore } from '../../stores/practiceStore'
import { RoleConfig } from '../../api/practice'
import ScenarioCard from '../../components/business/practice/ScenarioCard'
import RoleSelector from '../../components/business/practice/RoleSelector'

type Step = 'select' | 'configure' | 'ready'

const PracticePage = () => {
  const navigate = useNavigate()
  const {
    scenarios,
    selectedScenario,
    selectedRoleConfig,
    isLoadingScenarios,
    scenarioError,
    fetchScenarios,
    selectScenario,
    setRoleConfig,
    startSession,
    resetSession
  } = usePracticeStore()

  const [currentStep, setCurrentStep] = useState<Step>('select')
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  useEffect(() => {
    fetchScenarios()
  }, [fetchScenarios])

  useEffect(() => {
    if (selectedScenario && currentStep === 'select') {
      setCurrentStep('configure')
    }
  }, [selectedScenario])

  // Navigate to chat page when session is ready
  useEffect(() => {
    if (currentStep === 'ready' && selectedRoleConfig) {
      navigate('/practice/chat')
    }
  }, [currentStep, selectedRoleConfig, navigate])

  const handleScenarioSelect = (scenario: typeof selectedScenario) => {
    selectScenario(scenario)
  }

  const handleRoleConfigChange = (config: RoleConfig) => {
    setRoleConfig(config)
  }

  const handleStartPractice = async () => {
    if (!selectedScenario || !selectedRoleConfig) return

    setIsStarting(true)
    setStartError(null)

    try {
      await startSession()
      // WebSocket connection will be handled in subsequent stories
      setCurrentStep('ready')
    } catch (error) {
      setStartError(error instanceof Error ? error.message : '启动对练失败')
    } finally {
      setIsStarting(false)
    }
  }

  const handleReset = () => {
    resetSession()
    setCurrentStep('select')
    setStartError(null)
  }

  const isRoleConfigComplete = selectedRoleConfig?.position_level &&
                                selectedRoleConfig?.personality &&
                                selectedRoleConfig?.decision_style

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">销售对练</h1>
          <p className="text-sm text-gray-500 mt-1">与AI客户进行实时销售演练</p>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-center justify-center gap-4">
          <StepIndicator number={1} label="选择场景" active={currentStep === 'select'} completed={currentStep !== 'select'} />
          <div className={`w-12 h-0.5 ${currentStep !== 'select' ? 'bg-primary' : 'bg-gray-300'}`} />
          <StepIndicator number={2} label="配置角色" active={currentStep === 'configure'} completed={currentStep === 'ready'} />
          <div className={`w-12 h-0.5 ${currentStep === 'ready' ? 'bg-primary' : 'bg-gray-300'}`} />
          <StepIndicator number={3} label="开始对练" active={currentStep === 'ready'} completed={false} />
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 pb-8">
        {/* Error Display */}
        {(scenarioError || startError) && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{scenarioError || startError}</p>
          </div>
        )}

        {/* Step 1: Scenario Selection */}
        {currentStep === 'select' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">选择练习场景</h2>
              <span className="text-sm text-gray-500">共 {scenarios.length} 个场景</span>
            </div>

            {isLoadingScenarios ? (
              <div className="grid gap-4 md:grid-cols-2">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="animate-pulse p-4 rounded-lg border-2 border-gray-200 bg-gray-100 h-32" />
                ))}
              </div>
            ) : scenarios.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <p className="text-gray-500">暂无可用场景</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {scenarios.map(scenario => (
                  <ScenarioCard
                    key={scenario.id}
                    scenario={scenario}
                    isSelected={selectedScenario?.id === scenario.id}
                    onClick={() => handleScenarioSelect(scenario)}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Role Configuration */}
        {currentStep === 'configure' && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">配置AI客户角色</h2>
                <p className="text-sm text-gray-500 mt-1">
                  当前场景: <span className="font-medium text-primary">{selectedScenario?.name}</span>
                </p>
              </div>
              <button
                onClick={() => {
                  selectScenario(null)
                  setCurrentStep('select')
                }}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                返回选择场景
              </button>
            </div>

            <RoleSelector
              selectedConfig={selectedRoleConfig}
              onChange={handleRoleConfigChange}
            />

            <div className="mt-8 flex justify-end">
              <button
                onClick={handleStartPractice}
                disabled={!isRoleConfigComplete || isStarting}
                className={`
                  px-6 py-3 rounded-lg font-medium transition-all duration-200
                  ${isRoleConfigComplete && !isStarting
                    ? 'bg-primary text-white hover:bg-primary/90 shadow-md'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }
                `}
              >
                {isStarting ? '准备中...' : '开始对练'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Ready State */}
        {currentStep === 'ready' && (
          <div className="bg-white rounded-xl shadow-sm p-8 text-center">
            <div className="w-16 h-16 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">对练已准备就绪</h2>
            <p className="text-gray-500 mb-6">
              AI客户角色已配置完成，WebSocket连接将在下一版本实现
            </p>

            <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
              <h3 className="font-medium text-gray-700 mb-2">当前配置</h3>
              <div className="space-y-2 text-sm">
                <p><span className="text-gray-500">场景:</span> {selectedScenario?.name}</p>
                <p><span className="text-gray-500">角色:</span> {selectedRoleConfig?.position_level} / {selectedRoleConfig?.personality} / {selectedRoleConfig?.decision_style}</p>
              </div>
            </div>

            <div className="flex justify-center gap-4">
              <button
                onClick={handleReset}
                className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                重新开始
              </button>
              <button
                onClick={() => navigate('/practice/chat')}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
              >
                进入对练
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

// Step Indicator Component
const StepIndicator = ({ number, label, active, completed }: { number: number; label: string; active: boolean; completed: boolean }) => (
  <div className="flex items-center gap-2">
    <div className={`
      w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
      ${completed ? 'bg-primary text-white' : active ? 'bg-primary text-white' : 'bg-gray-200 text-gray-500'}
    `}>
      {completed ? (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : number}
    </div>
    <span className={`text-sm ${active ? 'text-primary font-medium' : 'text-gray-500'}`}>{label}</span>
  </div>
)

export default PracticePage
