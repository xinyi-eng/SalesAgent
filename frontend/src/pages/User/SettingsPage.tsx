/**
 * SettingsPage - User settings and preferences
 *
 * Features:
 * - Account settings (password, email)
 * - Notification preferences
 * - AI behavior preferences
 * - Privacy settings
 * - Theme settings
 *
 * Story: 2.4 个人设置
 */
import { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import authApi from '../../api/auth'

const SettingsPage = () => {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('account')

  // Account settings
  const [email, setEmail] = useState(user?.email || '')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // Notification settings
  const [notifications, setNotifications] = useState({
    email_summary: true,
    weekly_report: true,
    practice_reminder: false,
    system_updates: true
  })

  // AI behavior settings
  const [aiSettings, setAiSettings] = useState({
    response_speed: 'normal', // fast, normal, slow
    ai_personality: 'professional', // professional, casual, aggressive
    hint_level: 'medium', // low, medium, high
    auto_phase_summary: true
  })

  // Theme settings
  const [theme, setTheme] = useState('light') // light, dark, system

  const [accountSaving, setAccountSaving] = useState(false)
  const [accountError, setAccountError] = useState<string | null>(null)

  const handleSaveAccount = async () => {
    if (newPassword && newPassword !== confirmPassword) {
      setAccountError('两次密码不一致')
      return
    }
    setAccountSaving(true)
    setAccountError(null)
    try {
      // 真实调用：邮箱 / 用户名（如果需要改）写回后端
      await authApi.updateMe({ email: email || undefined })
      setPassword('')
      setNewPassword('')
      setConfirmPassword('')
      alert('账号设置已保存')
    } catch (err: any) {
      setAccountError(err?.response?.data?.detail || err?.message || '保存失败')
    } finally {
      setAccountSaving(false)
    }
  }

  const handleSaveNotifications = async () => {
    // 通知偏好后端暂未提供独立端点；先持久化到 localStorage
    try {
      localStorage.setItem('sa:notifications', JSON.stringify(notifications))
      alert('通知设置已保存到本地（后端尚未提供通知偏好接口）')
    } catch {
      alert('保存失败')
    }
  }

  const handleSaveAiSettings = async () => {
    // AI 行为偏好后端暂未提供；持久化到 localStorage
    try {
      localStorage.setItem('sa:ai_settings', JSON.stringify(aiSettings))
      alert('AI 行为已保存到本地（后端尚未提供 AI 偏好接口）')
    } catch {
      alert('保存失败')
    }
  }

  const tabs = [
    { key: 'account', label: '账号设置' },
    { key: 'notifications', label: '通知偏好' },
    { key: 'ai', label: 'AI行为' },
    { key: 'appearance', label: '外观' }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">设置</h1>
          <p className="text-sm text-gray-500 mt-1">管理您的账号和偏好设置</p>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-48 flex-shrink-0">
            <nav className="space-y-1">
              {tabs.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`
                    w-full text-left px-4 py-2 rounded-lg text-sm font-medium transition-colors
                    ${activeTab === tab.key
                      ? 'bg-primary text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                    }
                  `}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 bg-white rounded-xl shadow-sm p-6">
            {/* Account Settings */}
            {activeTab === 'account' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">账号信息</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                      <input
                        type="text"
                        value={user?.username || ''}
                        disabled
                        className="w-full max-w-md px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500"
                      />
                    </div>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">修改密码</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">新密码</label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleSaveAccount}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存修改
                  </button>
                </div>
              </div>
            )}

            {/* Notification Settings */}
            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">通知偏好</h2>
                  <div className="space-y-4">
                    {[
                      { key: 'email_summary', label: '每日练习摘要邮件', description: '每天发送练习情况汇总' },
                      { key: 'weekly_report', label: '每周报告', description: '每周一发送上周练习报告' },
                      { key: 'practice_reminder', label: '练习提醒', description: '提醒您保持练习习惯' },
                      { key: 'system_updates', label: '系统更新', description: '接收产品更新和功能通知' }
                    ].map(item => (
                      <div key={item.key} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{item.label}</p>
                          <p className="text-sm text-gray-500">{item.description}</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={notifications[item.key as keyof typeof notifications]}
                            onChange={(e) => setNotifications({
                              ...notifications,
                              [item.key]: e.target.checked
                            })}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleSaveNotifications}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存设置
                  </button>
                </div>
              </div>
            )}

            {/* AI Behavior Settings */}
            {activeTab === 'ai' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">AI客户行为</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">AI响应速度</label>
                      <select
                        value={aiSettings.response_speed}
                        onChange={(e) => setAiSettings({ ...aiSettings, response_speed: e.target.value })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="fast">快速 (即时响应)</option>
                        <option value="normal">正常 (1-2秒延迟)</option>
                        <option value="slow">慢速 (3-5秒延迟)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">AI人格风格</label>
                      <select
                        value={aiSettings.ai_personality}
                        onChange={(e) => setAiSettings({ ...aiSettings, ai_personality: e.target.value })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="professional">专业型</option>
                        <option value="casual">随和型</option>
                        <option value="aggressive">强硬型</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">提示级别</label>
                      <select
                        value={aiSettings.hint_level}
                        onChange={(e) => setAiSettings({ ...aiSettings, hint_level: e.target.value })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="low">低 (几乎不提示)</option>
                        <option value="medium">中 (适度提示)</option>
                        <option value="high">高 (频繁提示)</option>
                      </select>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">自动阶段总结</p>
                        <p className="text-sm text-gray-500">每个阶段结束时自动生成AI总结</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={aiSettings.auto_phase_summary}
                          onChange={(e) => setAiSettings({ ...aiSettings, auto_phase_summary: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleSaveAiSettings}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存设置
                  </button>
                </div>
              </div>
            )}

            {/* Appearance Settings */}
            {activeTab === 'appearance' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">外观主题</h2>
                  <div className="grid grid-cols-3 gap-4 max-w-md">
                    {[
                      { value: 'light', label: '浅色', preview: 'bg-white border-gray-300' },
                      { value: 'dark', label: '深色', preview: 'bg-gray-800 border-gray-600' },
                      { value: 'system', label: '跟随系统', preview: 'bg-gradient-to-r from-white to-gray-800 border-gray-400' }
                    ].map(item => (
                      <button
                        key={item.value}
                        onClick={() => setTheme(item.value)}
                        className={`
                          p-4 rounded-lg border-2 transition-all
                          ${theme === item.value ? 'border-primary' : 'border-gray-200 hover:border-gray-300'}
                        `}
                      >
                        <div className={`w-full h-16 rounded-lg mb-2 ${item.preview}`} />
                        <p className="text-sm font-medium text-gray-900">{item.label}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">危险操作</h2>
                  <div className="space-y-4">
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                      <p className="font-medium text-red-700">注销账号</p>
                      <p className="text-sm text-red-600 mt-1">永久删除您的账号和所有数据，此操作不可恢复</p>
                      <button className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm">
                        注销账号
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage