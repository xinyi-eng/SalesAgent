/**
 * AuditManagementPage - Scenario audit workflow
 *
 * Features:
 * - List scenarios pending audit
 * - Approve/Reject scenarios
 * - View audit history
 * - Bulk operations
 *
 * Story: 4.2 场景审核管理
 */
import { useState, useEffect } from 'react'

interface PendingScenario {
  id: string
  name: string
  description: string
  type: string
  category: string
  submitter: string
  submitted_at: string
  version: number
}

const AuditManagementPage = () => {
  const [pendingScenarios, setPendingScenarios] = useState<PendingScenario[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'pending' | 'approved' | 'rejected'>('pending')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadPendingAudits()
  }, [activeTab])

  const loadPendingAudits = async () => {
    setIsLoading(true)
    await new Promise(resolve => setTimeout(resolve, 600))

    const demoScenarios: PendingScenario[] = [
      {
        id: '1',
        name: '医疗器械采购谈判',
        description: '针对医疗器械采购的谈判场景',
        type: 'business_dinner',
        category: 'medical',
        submitter: 'user@company.com',
        submitted_at: '2024-01-15T10:30:00Z',
        version: 1
      },
      {
        id: '2',
        name: 'IT服务方案报价',
        description: 'IT服务方案报价的谈判场景',
        type: 'online_meeting',
        category: 'it_services',
        submitter: 'admin@company.com',
        submitted_at: '2024-01-14T15:00:00Z',
        version: 2
      },
      {
        id: '3',
        name: '制造业设备更新',
        description: '制造业设备更新换代的采购谈判',
        type: 'factory_visit',
        category: 'manufacturing',
        submitter: 'user2@company.com',
        submitted_at: '2024-01-13T09:00:00Z',
        version: 1
      }
    ]
    setPendingScenarios(demoScenarios)
    setIsLoading(false)
  }

  const handleApprove = async (id: string) => {
    await new Promise(resolve => setTimeout(resolve, 500))
    setPendingScenarios(prev => prev.filter(s => s.id !== id))
  }

  const handleReject = async (id: string) => {
    await new Promise(resolve => setTimeout(resolve, 500))
    setPendingScenarios(prev => prev.filter(s => s.id !== id))
  }

  const handleBulkApprove = async () => {
    await new Promise(resolve => setTimeout(resolve, 500))
    setPendingScenarios(prev => prev.filter(s => !selectedIds.has(s.id)))
    setSelectedIds(new Set())
  }

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">场景审核</h1>
              <p className="text-sm text-gray-500 mt-1">审核用户提交的练习场景</p>
            </div>
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">已选择 {selectedIds.size} 项</span>
                <button
                  onClick={handleBulkApprove}
                  className="px-4 py-2 bg-success text-white rounded-lg hover:bg-success/90"
                >
                  批量通过
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex gap-4">
            {[
              { key: 'pending', label: '待审核', count: 3 },
              { key: 'approved', label: '已通过', count: 21 },
              { key: 'rejected', label: '已拒绝', count: 5 }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as typeof activeTab)}
                className={`
                  py-3 text-sm font-medium border-b-2 transition-colors
                  ${activeTab === tab.key
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                  }
                `}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse bg-white rounded-lg p-4 h-32" />
            ))}
          </div>
        ) : pendingScenarios.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-gray-500">
              {activeTab === 'pending' ? '暂无待审核场景' : activeTab === 'approved' ? '暂无已通过场景' : '暂无已拒绝场景'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {pendingScenarios.map(scenario => (
              <div key={scenario.id} className="bg-white rounded-lg p-6 shadow-sm">
                <div className="flex items-start gap-4">
                  {/* Selection */}
                  <input
                    type="checkbox"
                    checked={selectedIds.has(scenario.id)}
                    onChange={() => toggleSelect(scenario.id)}
                    className="mt-1 w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary/20"
                  />

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{scenario.name}</h3>
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                        v{scenario.version}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{scenario.description}</p>
                    <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                      <span>提交者: {scenario.submitter}</span>
                      <span>提交时间: {formatDate(scenario.submitted_at)}</span>
                      <span>类型: {scenario.type}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  {activeTab === 'pending' && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(scenario.id)}
                        className="px-4 py-2 bg-success text-white rounded-lg hover:bg-success/90 text-sm"
                      >
                        通过
                      </button>
                      <button
                        onClick={() => handleReject(scenario.id)}
                        className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                      >
                        拒绝
                      </button>
                      <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm">
                        查看详情
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default AuditManagementPage