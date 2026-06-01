/**
 * AdminDashboardPage - Admin analytics dashboard
 *
 * Features:
 * - Platform-wide statistics
 * - User activity overview
 * - Scenario usage analytics
 * - System health monitoring
 *
 * Story: 4.1 管理员仪表盘
 */
import { useState, useEffect } from 'react'

interface AdminStats {
  total_users: number
  active_users_today: number
  total_practices: number
  practices_today: number
  avg_score: number
  total_scenarios: number
  pending_audits: number
  system_health: 'healthy' | 'warning' | 'critical'
  popular_scenarios: Array<{ name: string; count: number }>
  daily_trend: Array<{ date: string; count: number }>
}

const AdminDashboardPage = () => {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadStats = async () => {
      setIsLoading(true)
      await new Promise(resolve => setTimeout(resolve, 800))
      setStats({
        total_users: 1250,
        active_users_today: 89,
        total_practices: 8430,
        practices_today: 156,
        avg_score: 74.2,
        total_scenarios: 24,
        pending_audits: 3,
        system_health: 'healthy',
        popular_scenarios: [
          { name: 'CRM系统需求挖掘', count: 1250 },
          { name: 'ERP报价谈判', count: 980 },
          { name: '工厂参观', count: 720 },
          { name: '陌拜电话', count: 540 },
          { name: '商务宴请', count: 380 }
        ],
        daily_trend: [
          { date: '01-15', count: 120 },
          { date: '01-14', count: 135 },
          { date: '01-13', count: 98 },
          { date: '01-12', count: 145 },
          { date: '01-11', count: 112 },
          { date: '01-10', count: 88 },
          { date: '01-09', count: 156 }
        ]
      })
      setIsLoading(false)
    }
    loadStats()
  }, [])

  const formatNumber = (num: number) => num.toLocaleString()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">管理后台</h1>
              <p className="text-sm text-gray-500 mt-1">平台运营数据概览</p>
            </div>
            <div className="flex items-center gap-3">
              {stats?.pending_audits ? (
                <button
                  onClick={() => window.location.href = '/admin/audits'}
                  className="px-4 py-2 bg-warning text-white rounded-lg hover:bg-warning/90 flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  {stats.pending_audits} 待审核
                </button>
              ) : null}
              <span className={`
                px-3 py-1 rounded-full text-sm font-medium
                ${stats?.system_health === 'healthy' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}
              `}>
                系统正常
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <p className="text-sm text-gray-500">总用户数</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{formatNumber(stats?.total_users || 0)}</p>
            <p className="text-xs text-success mt-1">+12% 本月</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <p className="text-sm text-gray-500">今日活跃</p>
            <p className="text-2xl font-bold text-primary mt-1">{formatNumber(stats?.active_users_today || 0)}</p>
            <p className="text-xs text-gray-500 mt-1">今日</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <p className="text-sm text-gray-500">总练习次数</p>
            <p className="text-2xl font-bold text-secondary mt-1">{formatNumber(stats?.total_practices || 0)}</p>
            <p className="text-xs text-gray-500 mt-1">历史累计</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <p className="text-sm text-gray-500">今日练习</p>
            <p className="text-2xl font-bold text-warning mt-1">{formatNumber(stats?.practices_today || 0)}</p>
            <p className="text-xs text-gray-500 mt-1">今日</p>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Daily Trend */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">每日练习趋势</h2>
            <div className="h-40 flex items-end gap-2">
              {stats?.daily_trend.map((item, idx) => (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2">
                  <div
                    className="w-full bg-primary/20 rounded-t hover:bg-primary/30 transition-colors"
                    style={{ height: `${(item.count / 160) * 100}%` }}
                  />
                  <span className="text-xs text-gray-500">{item.date}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Popular Scenarios */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">热门场景</h2>
            <div className="space-y-3">
              {stats?.popular_scenarios.map((scenario, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <span className="w-6 h-6 bg-gray-100 rounded text-xs font-medium text-gray-600 flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">{scenario.name}</span>
                      <span className="text-sm text-gray-500">{scenario.count}</span>
                    </div>
                    <div className="mt-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${(scenario.count / 1250) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">管理功能</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => window.location.href = '/admin/scenarios'}
              className="p-4 border border-gray-200 rounded-lg hover:border-primary hover:bg-primary/5 transition-all text-center"
            >
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-900">场景管理</p>
              <p className="text-xs text-gray-500 mt-1">{stats?.total_scenarios} 个场景</p>
            </button>

            <button
              onClick={() => window.location.href = '/admin/users'}
              className="p-4 border border-gray-200 rounded-lg hover:border-secondary hover:bg-secondary/5 transition-all text-center"
            >
              <div className="w-12 h-12 bg-secondary/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                <svg className="w-6 h-6 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-900">用户管理</p>
              <p className="text-xs text-gray-500 mt-1">{stats?.total_users} 用户</p>
            </button>

            <button
              onClick={() => window.location.href = '/admin/audits'}
              className="p-4 border border-gray-200 rounded-lg hover:border-warning hover:bg-warning/5 transition-all text-center relative"
            >
              {stats?.pending_audits ? (
                <span className="absolute top-2 right-2 w-5 h-5 bg-warning text-white text-xs rounded-full flex items-center justify-center">
                  {stats.pending_audits}
                </span>
              ) : null}
              <div className="w-12 h-12 bg-warning/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                <svg className="w-6 h-6 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-900">审核管理</p>
              <p className="text-xs text-gray-500 mt-1">{stats?.pending_audits} 待审核</p>
            </button>

            <button
              onClick={() => window.location.href = '/admin/settings'}
              className="p-4 border border-gray-200 rounded-lg hover:border-success hover:bg-success/5 transition-all text-center"
            >
              <div className="w-12 h-12 bg-success/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                <svg className="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-900">系统设置</p>
              <p className="text-xs text-gray-500 mt-1">平台配置</p>
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default AdminDashboardPage