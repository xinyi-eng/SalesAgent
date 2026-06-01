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
import ScoreChart from '../../components/business/practice/ScoreChart'

interface UserStats {
  total_practice_sessions: number
  total_practice_time: number
  average_scores: {
    communication: number
    persuasion: number
    closing: number
    spin: number
  }
  strongest_skill: string
  weakest_skill: string
}

const SKILL_LABELS: Record<string, string> = {
  communication: '沟通能力',
  persuasion: '说服能力',
  closing: '促成能力',
  spin: '扭转能力'
}

const ProfilePage = () => {
  const { user } = useAuth()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    fullName: user?.full_name || '',
    bio: ''
  })

  useEffect(() => {
    // Simulate loading stats
    const loadStats = async () => {
      setIsLoading(true)
      await new Promise(resolve => setTimeout(resolve, 800))
      setStats({
        total_practice_sessions: 24,
        total_practice_time: 360,
        average_scores: {
          communication: 82,
          persuasion: 75,
          closing: 70,
          spin: 85
        },
        strongest_skill: 'spin',
        weakest_skill: 'closing'
      })
      setIsLoading(false)
    }
    loadStats()
  }, [])

  const handleSaveProfile = async () => {
    // In production, call API
    await new Promise(resolve => setTimeout(resolve, 500))
    setIsEditing(false)
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

        {/* Radar Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">能力雷达图</h2>
          <div className="flex justify-center">
            <ScoreChart
              scores={{
                communication_score: stats?.average_scores.communication || 0,
                persuasion_score: stats?.average_scores.persuasion || 0,
                closing_score: stats?.average_scores.closing || 0,
                spin_score: stats?.average_scores.spin || 0
              }}
              size={300}
            />
          </div>
        </div>

        {/* Skills Self-Assessment */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">自我评估</h2>
          <p className="text-sm text-gray-500 mb-4">
            滑动调整您的各项技能熟练度
          </p>
          <div className="space-y-4">
            {Object.entries(SKILL_LABELS).map(([key, label]) => {
              const score = stats?.average_scores[key as keyof typeof stats.average_scores] || 0
              return (
                <div key={key} className="flex items-center gap-4">
                  <span className="w-24 text-sm text-gray-700">{label}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <span className="w-10 text-sm font-medium text-gray-900 text-right">{score}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">最近活动</h2>
          <div className="space-y-4">
            {[
              { date: '2024-01-15', action: '完成练习', detail: 'CRM系统需求挖掘 - 82分' },
              { date: '2024-01-14', action: '生成报告', detail: 'ERP报价谈判 - 复盘报告' },
              { date: '2024-01-13', action: '开始练习', detail: '陌拜电话 - 开场破冰' }
            ].map((item, idx) => (
              <div key={idx} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{item.action}</p>
                  <p className="text-sm text-gray-500">{item.detail}</p>
                </div>
                <span className="text-xs text-gray-400">{item.date}</span>
              </div>
            ))}
          </div>
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