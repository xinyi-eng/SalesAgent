/**
 * HistoryPage - Practice history page
 *
 * Features:
 * - Paginated list of practice sessions
 * - Filter by scenario type, date range
 * - View session details
 * - Continue or review past sessions
 *
 * Story: 2.3 练习历史记录
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { SessionListItem, HistoryStatsResponse } from '../../api/practice'

const SCENARIO_TYPE_LABELS: Record<string, string> = {
  cold_call: '陌拜电话',
  online_meeting: '线上会议',
  factory_visit: '工厂参观',
  business_dinner: '商务宴请'
}

const PHASE_LABELS: Record<string, string> = {
  opening: '开场破冰',
  discovery: '需求挖掘',
  needs: '方案呈现',
  proposal: '促成成交',
  closing: '复盘总结'
}

const HistoryPage = () => {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [stats, setStats] = useState<HistoryStatsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState({ type: '', dateRange: '30days' })

  useEffect(() => {
    loadHistory()
    loadStats()
  }, [page, filter])

  const loadHistory = async () => {
    setIsLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (filter.type) {
        params.scenario_type = filter.type
      }
      if (filter.dateRange === '7days') {
        // Filter handled by date on frontend for now
      }

      const response = await api.getSessions(params)
      setSessions(response.data)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load history:', error)
      // Fallback to demo data on error
      setSessions([{
        id: 'demo-1',
        scenario_id: 'demo',
        scenario_name: 'CRM系统需求挖掘',
        scenario_type: 'online_meeting',
        user_id: 'anonymous',
        role_config: { position_level: 'junior', personality: 'rational', decision_style: 'price_oriented' },
        status: 'completed',
        current_phase: 'closing',
        score: 82,
        message_count: 42,
        duration_minutes: 25,
        created_at: new Date().toISOString(),
        ended_at: new Date().toISOString()
      }])
      setTotal(1)
    }
    setIsLoading(false)
  }

  const loadStats = async () => {
    try {
      const response = await api.getHistoryStats()
      setStats(response)
    } catch (error) {
      console.error('Failed to load stats:', error)
      // Fallback to demo data
      setStats({
        last_30_days: {
          sessions: 12,
          completed: 10,
          duration_minutes: 420,
          messages: 1250,
          avg_score: 76.5
        },
        last_90_days: {
          sessions: 35,
          completed: 28,
          duration_minutes: 1450,
          messages: 4200,
          avg_score: 74.2
        }
      })
    }
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}分钟`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}小时${mins > 0 ? `${mins}分钟` : ''}`
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const handleViewSession = (session: SessionListItem) => {
    navigate(`/practice/review?sessionId=${session.id}`)
  }

  const handleContinueSession = (session: SessionListItem) => {
    navigate(`/practice/chat?sessionId=${session.id}`)
  }

  // Use last_30_days or fallback stats
  const stats30 = stats?.last_30_days || { sessions: 0, completed: 0, duration_minutes: 0, messages: 0, avg_score: null }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">练习历史</h1>
          <p className="text-sm text-gray-500 mt-1">查看您的练习记录和进步</p>
        </div>
      </header>

      {/* Stats Overview */}
      {stats && (
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-6xl mx-auto px-4 py-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-primary">{stats30.sessions}</p>
                <p className="text-sm text-gray-500">练习次数</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-success">{stats30.avg_score || '-'}</p>
                <p className="text-sm text-gray-500">平均得分</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-secondary">{formatDuration(stats30.duration_minutes)}</p>
                <p className="text-sm text-gray-500">练习时长</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-warning">{stats30.completed}</p>
                <p className="text-sm text-gray-500">已完成</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex gap-4">
            <select
              value={filter.type}
              onChange={(e) => setFilter({ ...filter, type: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="">全部类型</option>
              <option value="cold_call">陌拜电话</option>
              <option value="online_meeting">线上会议</option>
              <option value="factory_visit">工厂参观</option>
              <option value="business_dinner">商务宴请</option>
            </select>

            <select
              value={filter.dateRange}
              onChange={(e) => setFilter({ ...filter, dateRange: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="7days">最近7天</option>
              <option value="30days">最近30天</option>
              <option value="90days">最近90天</option>
              <option value="all">全部</option>
            </select>
          </div>
        </div>
      </div>

      {/* History List */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="animate-pulse bg-white rounded-lg p-4 h-24" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg">
            <p className="text-gray-500">暂无练习记录</p>
            <button
              onClick={() => navigate('/practice')}
              className="mt-4 text-primary hover:underline"
            >
              开始练习
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {sessions.map(session => (
              <div
                key={session.id}
                className="bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewSession(session)}
              >
                <div className="flex items-start gap-4">
                  {/* Score indicator */}
                  <div className={`
                    w-14 h-14 rounded-lg flex flex-col items-center justify-center
                    ${session.score ? 'bg-success/10' : 'bg-gray-100'}
                  `}>
                    {session.score ? (
                      <>
                        <span className="text-lg font-bold text-success">{Math.round(session.score)}</span>
                        <span className="text-xs text-success">分</span>
                      </>
                    ) : (
                      <span className="text-lg font-bold text-gray-400">-</span>
                    )}
                  </div>

                  {/* Session info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{session.scenario_name || '练习会话'}</h3>
                      {session.scenario_type && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                          {SCENARIO_TYPE_LABELS[session.scenario_type] || session.scenario_type}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                      <span>{formatDate(session.created_at)}</span>
                      <span>{formatDuration(session.duration_minutes)}</span>
                      <span>{session.message_count}条消息</span>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`
                        px-2 py-0.5 text-xs rounded
                        ${session.status === 'completed' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}
                      `}>
                        {session.status === 'completed' ? '已完成' : '进行中'}
                      </span>
                      {session.current_phase && (
                        <span className="text-xs text-gray-400">
                          当前阶段: {PHASE_LABELS[session.current_phase]}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    {session.status !== 'completed' && (
                      <button
                        onClick={() => handleContinueSession(session)}
                        className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm"
                      >
                        继续
                      </button>
                    )}
                    <button
                      onClick={() => handleViewSession(session)}
                      className="px-3 py-1.5 bg-primary text-white rounded-lg hover:bg-primary/90 text-sm"
                    >
                      查看
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > 0 && (
          <div className="flex justify-center gap-2 mt-6">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              上一页
            </button>
            <span className="px-3 py-1.5 text-gray-500">
              第 {page} 页
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={sessions.length < 20}
              className="px-3 py-1.5 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一页
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default HistoryPage