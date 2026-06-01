/**
 * ScenarioManagementPage - Admin scenario management page
 *
 * Features:
 * - List all scenarios (builtin + custom)
 * - Filter by category, sub_category, type
 * - Create/Edit/Delete scenarios
 * - Audit workflow for custom scenarios
 *
 * Story: 1.5 场景库管理
 */
import { useEffect, useState } from 'react'
import { Scenario } from '../../api/practice'
import ScenarioCard from '../../components/business/practice/ScenarioCard'
import ScenarioFormModal, { ScenarioFormData } from '../../components/business/practice/ScenarioFormModal'

type FilterTab = 'all' | 'builtin' | 'custom'
type StatusFilter = 'approved' | 'pending' | 'rejected' | 'all'

const ScenarioManagementPage = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [activeTab, setActiveTab] = useState<FilterTab>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')

  // Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [editingScenario, setEditingScenario] = useState<Scenario | null>(null)

  // Load scenarios
  const loadScenarios = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // In production, call API
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800))

      // Demo data
      const demoScenarios: Scenario[] = [
        {
          id: '1',
          name: 'CRM系统需求挖掘',
          description: '客户对CRM系统有兴趣，需要挖掘具体需求',
          type: 'online_meeting',
          category: 'enterprise_software',
          sub_category: 'crm',
          is_builtin: true,
          status: 'approved',
          default_role_config: {},
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '2',
          name: 'ERP系统报价谈判',
          description: '客户对ERP系统报价有异议，需要处理价格谈判',
          type: 'business_dinner',
          category: 'enterprise_software',
          sub_category: 'erp',
          is_builtin: true,
          status: 'approved',
          default_role_config: {},
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '3',
          name: '机械设备海外拓展',
          description: '制造业客户拓展海外市场，需要建立销售渠道',
          type: 'factory_visit',
          category: 'manufacturing',
          sub_category: 'machinery',
          is_builtin: true,
          status: 'approved',
          default_role_config: {},
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ]
      setScenarios(demoScenarios)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载场景失败')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadScenarios()
  }, [])

  // Filter scenarios
  const filteredScenarios = scenarios.filter(scenario => {
    // Tab filter
    if (activeTab === 'builtin' && !scenario.is_builtin) return false
    if (activeTab === 'custom' && scenario.is_builtin) return false

    // Status filter
    if (statusFilter !== 'all' && scenario.status !== statusFilter) return false

    // Category filter
    if (categoryFilter && scenario.category !== categoryFilter) return false

    // Search
    if (searchQuery && !scenario.name.toLowerCase().includes(searchQuery.toLowerCase())) return false

    return true
  })

  // Handle create scenario
  const handleCreateScenario = async (data: ScenarioFormData) => {
    // In production, call API
    // await api.createScenario(data)
    console.log('Create scenario:', data)
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  // Handle edit scenario
  const handleEditScenario = async (data: ScenarioFormData) => {
    if (!editingScenario) return
    // In production, call API
    // await api.updateScenario(editingScenario.id, data)
    console.log('Edit scenario:', editingScenario.id, data)
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  // Handle delete scenario
  const handleDeleteScenario = async (scenario: Scenario) => {
    if (scenario.is_builtin) {
      alert('内置场景不能删除')
      return
    }

    if (!confirm(`确定要删除场景"${scenario.name}"吗？`)) return

    // In production, call API
    // await api.deleteScenario(scenario.id)
    console.log('Delete scenario:', scenario.id)
    await new Promise(resolve => setTimeout(resolve, 500))
    loadScenarios()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">场景库管理</h1>
              <p className="text-sm text-gray-500 mt-1">管理销售对练场景</p>
            </div>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              创建场景
            </button>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex flex-wrap items-center gap-4">
            {/* Tab Filter */}
            <div className="flex gap-2">
              {[
                { key: 'all', label: '全部场景' },
                { key: 'builtin', label: '内置场景' },
                { key: 'custom', label: '自定义' }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as FilterTab)}
                  className={`
                    px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                    ${activeTab === tab.key
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }
                  `}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search */}
            <div className="flex-1 max-w-xs">
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索场景..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
                />
              </div>
            </div>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
            >
              <option value="">全部分类</option>
              <option value="enterprise_software">企业软件</option>
              <option value="manufacturing">制造业</option>
              <option value="consulting">咨询业</option>
              <option value="service">服务业</option>
            </select>

            {/* Status Filter */}
            {activeTab === 'custom' && (
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
              >
                <option value="all">全部状态</option>
                <option value="pending">待审核</option>
                <option value="approved">已通过</option>
                <option value="rejected">已拒绝</option>
              </select>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="animate-pulse p-4 rounded-lg border-2 border-gray-200 bg-gray-100 h-40" />
            ))}
          </div>
        ) : filteredScenarios.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="text-gray-500">暂无场景</p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="mt-4 text-primary hover:underline"
            >
              创建第一个场景
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredScenarios.map(scenario => (
              <div key={scenario.id} className="relative">
                <ScenarioCard
                  scenario={scenario}
                  isSelected={false}
                  onClick={() => {}}
                />
                {/* Action buttons */}
                <div className="absolute top-2 right-2 flex gap-1">
                  <button
                    onClick={() => setEditingScenario(scenario)}
                    className="p-1.5 bg-white text-gray-600 rounded-lg hover:bg-gray-100 shadow-sm"
                    title="编辑"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  {!scenario.is_builtin && (
                    <button
                      onClick={() => handleDeleteScenario(scenario)}
                      className="p-1.5 bg-white text-red-600 rounded-lg hover:bg-red-50 shadow-sm"
                      title="删除"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                </div>
                {/* Builtin badge */}
                {scenario.is_builtin && (
                  <div className="absolute top-2 left-2">
                    <span className="px-2 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full">
                      内置
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      <ScenarioFormModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateScenario}
        mode="create"
      />

      {/* Edit Modal */}
      <ScenarioFormModal
        isOpen={!!editingScenario}
        onClose={() => setEditingScenario(null)}
        onSubmit={handleEditScenario}
        scenario={editingScenario}
        mode="edit"
      />
    </div>
  )
}

export default ScenarioManagementPage