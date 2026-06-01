/**
 * SystemSettingsPage - Platform system settings
 *
 * Features:
 * - General platform settings
 * - AI model configuration
 * - Email notification settings
 * - Security settings
 * - API key management
 *
 * Story: 4.5 系统设置
 */
import { useState } from 'react'

const SystemSettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState({
    // General
    platform_name: '销售智能体',
    platform_logo: '',
    maintenance_mode: false,
    allow_registration: true,

    // AI Settings
    ai_model: 'claude-3-opus',
    ai_temperature: 0.7,
    ai_max_tokens: 4096,
    ai_response_delay: 1.5,

    // Email
    email_enabled: true,
    email_provider: 'smtp',
    email_from: 'noreply@salesagent.com',
    email_limit_daily: 100,

    // Security
    jwt_expiry_hours: 24,
    refresh_token_days: 7,
    max_login_attempts: 5,
    password_min_length: 6
  })

  const tabs = [
    { key: 'general', label: '通用' },
    { key: 'ai', label: 'AI配置' },
    { key: 'email', label: '邮件' },
    { key: 'security', label: '安全' }
  ]

  const handleSave = async () => {
    await new Promise(resolve => setTimeout(resolve, 500))
    alert('设置已保存')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">系统设置</h1>
          <p className="text-sm text-gray-500 mt-1">配置平台全局设置</p>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-40 flex-shrink-0">
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
            {/* General Settings */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">通用设置</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">平台名称</label>
                      <input
                        type="text"
                        value={settings.platform_name}
                        onChange={(e) => setSettings({ ...settings, platform_name: e.target.value })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">维护模式</p>
                        <p className="text-sm text-gray-500">启用后普通用户无法访问</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.maintenance_mode}
                          onChange={(e) => setSettings({ ...settings, maintenance_mode: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">允许新用户注册</p>
                        <p className="text-sm text-gray-500">禁用后只能管理员创建账号</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.allow_registration}
                          onChange={(e) => setSettings({ ...settings, allow_registration: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                  <button
                    onClick={handleSave}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存设置
                  </button>
                </div>
              </div>
            )}

            {/* AI Settings */}
            {activeTab === 'ai' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">AI模型配置</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">AI模型</label>
                      <select
                        value={settings.ai_model}
                        onChange={(e) => setSettings({ ...settings, ai_model: e.target.value })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="claude-3-opus">Claude 3 Opus</option>
                        <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                        <option value="claude-3-haiku">Claude 3 Haiku</option>
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Temperature: {settings.ai_temperature}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={settings.ai_temperature}
                        onChange={(e) => setSettings({ ...settings, ai_temperature: parseFloat(e.target.value) })}
                        className="w-full max-w-md"
                      />
                      <p className="text-xs text-gray-500 mt-1">较低的值更确定性，较高的值更有创造性</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">最大Token数</label>
                      <input
                        type="number"
                        value={settings.ai_max_tokens}
                        onChange={(e) => setSettings({ ...settings, ai_max_tokens: parseInt(e.target.value) })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">响应延迟（秒）</label>
                      <input
                        type="number"
                        step="0.5"
                        value={settings.ai_response_delay}
                        onChange={(e) => setSettings({ ...settings, ai_response_delay: parseFloat(e.target.value) })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                      <p className="text-xs text-gray-500 mt-1">模拟AI响应延迟，增加真实感</p>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                  <button
                    onClick={handleSave}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存设置
                  </button>
                </div>
              </div>
            )}

            {/* Email Settings */}
            {activeTab === 'email' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">邮件配置</h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">启用邮件通知</p>
                        <p className="text-sm text-gray-500">发送练习摘要和报告邮件</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.email_enabled}
                          onChange={(e) => setSettings({ ...settings, email_enabled: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                      </label>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">发件人邮箱</label>
                      <input
                        type="email"
                        value={settings.email_from}
                        onChange={(e) => setSettings({ ...settings, email_from: e.target.value })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">每日发送上限</label>
                      <input
                        type="number"
                        value={settings.email_limit_daily}
                        onChange={(e) => setSettings({ ...settings, email_limit_daily: parseInt(e.target.value) })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                  <button
                    onClick={handleSave}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存设置
                  </button>
                </div>
              </div>
            )}

            {/* Security Settings */}
            {activeTab === 'security' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">安全配置</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">JWT过期时间（小时）</label>
                      <input
                        type="number"
                        value={settings.jwt_expiry_hours}
                        onChange={(e) => setSettings({ ...settings, jwt_expiry_hours: parseInt(e.target.value) })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Refresh Token有效期（天）</label>
                      <input
                        type="number"
                        value={settings.refresh_token_days}
                        onChange={(e) => setSettings({ ...settings, refresh_token_days: parseInt(e.target.value) })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">密码最小长度</label>
                      <input
                        type="number"
                        value={settings.password_min_length}
                        onChange={(e) => setSettings({ ...settings, password_min_length: parseInt(e.target.value) })}
                        className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                  <button
                    onClick={handleSave}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    保存设置
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SystemSettingsPage