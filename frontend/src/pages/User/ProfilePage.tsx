/**
 * ProfilePage - User profile and statistics page
 *
 * Features:
 * - User info display and edit
 * - Practice statistics radar chart
 * - Skill self-assessment
 * - Activity history
 *
 * Story: 2.2 用户画像管理
 */
import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import profileApi, { UserStats as ApiUserStats } from '../../api/profile'
import authApi from '../../api/auth'
import practiceApi, { SessionListItem } from '../../api/practice'
import ScoreChart from '../../components/business/practice/ScoreChart'

interface UserStats extends ApiUserStats {}

const SKILL_LABELS: Record<string, string> = {
  communication: '沟通能力',
  persuasion: '说服能力',
  closing: '促成能力',
  spin: '扭转能力',
  // 6 维扩展
  opening: '开场破冰',
  discovery: '需求挖掘',
  presentation: '产品呈现',
  objection: '异议处理',
  rapport: '关系建立',
}

const ProfilePage = () => {
  const { user, refreshUser } = useAuth()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [recentSessions, setRecentSessions] = useState<SessionListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({
    fullName: user?.full_name || '',
    bio: user?.bio || ''
  })

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // 并行拉统计和最近 3 个 session
      const [statsData, sessionsData] = await Promise.all([
        profileApi.getStats(),
        practiceApi.getSessions({ page: 1, page_size: 3 }),
      ])
      setStats(statsData)
      setRecentSessions(sessionsData.data || [])
    } catch (err: any) {
      console.error('Failed to load profile stats:', err)
      setError(err?.response?.data?.detail || err?.message || '加载用户统计失败')
      setStats(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveProfile = async () => {
    if (!user) return
    setIsSaving(true)
    setSaveError(null)
    try {
      await authApi.updateMe({
        full_name: editForm.fullName,
        bio: editForm.bio,
      })
      // 触发 AuthContext 重新拉 /auth/me 刷新 user
      await refreshUser()
      setIsEditing(false)
    } catch (err: any) {
      console.error('Failed to save profile:', err)
      setSaveError(err?.response?.data?.detail || err?.message || '保存失败')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-gray-500">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-secondary">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="flex items-center gap-6">
            {/* Avatar */}
            <div className="relative">
              <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center text-3xl font-bold text-primary">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <button className="absolute bottom-0 right-0 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>

            {/* User Info */}
            <div className="flex-1 text-white">
              <h1 className="text-2xl font-bold">{user?.full_name || user?.username}</h1>
              <p className="text-white/80 mt-1">@{user?.username}</p>
              <p className="text-white/60 text-sm mt-2">{user?.email}</p>
            </div>

            {/* Edit Button */}
            <button
              onClick={() => setIsEditing(true)}
              className="px-4 py-2 bg-white/20 text-white rounded-lg hover:bg-white/30 transition-colors"
            >
              编辑资料
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '练习次数', value: stats?.total_practice_sessions || 0, icon: '📝' },
            { label: '练习时长', value: `${Math.floor((stats?.total_practice_time || 0) / 60)}h`, icon: '⏱️' },
            { label: '最强项', value: SKILL_LABELS[stats?.strongest_skill || 'communication'], icon: '💪' },
            { label: '待提升', value: SKILL_LABELS[stats?.weakest_skill || 'closing'], icon: '📈' }
          ].map((item, idx) => (
            <div key={idx} className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl mb-1">{item.icon}</div>
              <p className="text-sm text-gray-500">{item.label}</p>
              <p className="text-lg font-semibold text-gray-900 mt-1">{item.value}</p>
            </div>
          ))}
        </div>

        {/* Radar Chart — 6 维度（用真实数据，从 stats.average_scores 拉） */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">能力雷达图</h2>
          <div className="flex justify-center">
            <ScoreChart
              scores={{
                // 优先用新的 6 维字段，没有就 fallback 到旧的 4 维
                opening: stats?.average_scores?.opening ?? stats?.average_scores?.communication ?? 0,
                discovery: stats?.average_scores?.discovery ?? stats?.average_scores?.persuasion ?? 0,
                presentation: stats?.average_scores?.presentation ?? 0,
                objection: stats?.average_scores?.objection ?? stats?.average_scores?.spin ?? 0,
                closing: stats?.average_scores?.closing ?? 0,
                rapport: stats?.average_scores?.rapport ?? 0,
              }}
              size={300}
            />
          </div>
        </div>

        {/* Skills Self-Assessment — 横向卡片布局，每张卡片内含名称+进度条+分数 */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">自我评估</h2>
          <p className="text-sm text-gray-500 mb-4">
            系统根据您的对练记录自动评估各项能力
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(SKILL_LABELS).map(([key, label]) => {
              const score = stats?.average_scores?.[key as keyof typeof stats.average_scores] || 0
              return (
                <div
                  key={key}
                  className="border border-gray-200 rounded-lg p-4 flex flex-col gap-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{label}</span>
                    <span className="text-2xl font-bold text-primary">{score}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-400">满分 100</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Recent Activity — 真实从 sessions-list 拉取，不再 hardcode */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">最近活动</h2>
          {recentSessions.length === 0 ? (
            <div className="text-center py-6 text-sm text-gray-500">
              暂无练习记录
            </div>
          ) : (
            <div className="space-y-4">
              {recentSessions.map((s) => {
                const action = s.status === 'completed' ? '完成练习' : s.status === 'active' ? '进行中' : '开始练习'
                const detail = s.score != null
                  ? `${s.scenario_name || '对练'} - ${s.score}分`
                  : s.scenario_name || '对练'
                return (
                  <div
                    key={s.id}
                    onClick={() => window.location.assign(`/practice/review?sessionId=${s.id}`)}
                    className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                  >
                    <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{action}</p>
                      <p className="text-sm text-gray-500 truncate">{detail}</p>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(s.created_at).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </main>

      {/* Edit Modal */}
      {isEditing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => setIsEditing(false)} />
          <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">编辑资料</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">姓名</label>
                <input
                  type="text"
                  value={editForm.fullName}
                  onChange={(e) => setEditForm({ ...editForm, fullName: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">个人简介</label>
                <textarea
                  value={editForm.bio}
                  onChange={(e) => setEditForm({ ...editForm, bio: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                  placeholder="介绍一下自己..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleSaveProfile}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProfilePage