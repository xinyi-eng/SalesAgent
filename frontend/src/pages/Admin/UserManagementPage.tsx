/**
 * UserManagementPage - Admin user management
 *
 * Features:
 * - List all users
 * - Search and filter users
 * - Edit user roles
 * - Disable/enable users
 * - View user activity
 *
 * Story: 4.3 用户管理
 */
import { useState, useEffect } from 'react'

interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: 'user' | 'admin' | 'pm' | 'fae'
  is_active: boolean
  total_sessions: number
  avg_score: number
  last_login: string
  created_at: string
}

const UserManagementPage = () => {
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  useEffect(() => {
    loadUsers()
  }, [searchQuery, roleFilter])

  const loadUsers = async () => {
    setIsLoading(true)
    await new Promise(resolve => setTimeout(resolve, 600))

    const demoUsers: User[] = [
      {
        id: '1',
        email: 'admin@company.com',
        username: 'admin',
        full_name: '系统管理员',
        role: 'admin',
        is_active: true,
        total_sessions: 156,
        avg_score: 82.5,
        last_login: '2024-01-15T10:30:00Z',
        created_at: '2024-01-01T00:00:00Z'
      },
      {
        id: '2',
        email: 'john.doe@company.com',
        username: 'johndoe',
        full_name: 'John Doe',
        role: 'user',
        is_active: true,
        total_sessions: 42,
        avg_score: 76.3,
        last_login: '2024-01-15T09:00:00Z',
        created_at: '2024-01-05T00:00:00Z'
      },
      {
        id: '3',
        email: 'jane.smith@company.com',
        username: 'janesmith',
        full_name: 'Jane Smith',
        role: 'user',
        is_active: true,
        total_sessions: 38,
        avg_score: 79.1,
        last_login: '2024-01-14T18:00:00Z',
        created_at: '2024-01-06T00:00:00Z'
      },
      {
        id: '4',
        email: 'bob.wilson@company.com',
        username: 'bobwilson',
        full_name: 'Bob Wilson',
        role: 'user',
        is_active: false,
        total_sessions: 12,
        avg_score: 65.0,
        last_login: '2024-01-10T14:00:00Z',
        created_at: '2024-01-08T00:00:00Z'
      }
    ]
    setUsers(demoUsers)
    setIsLoading(false)
  }

  const handleToggleActive = async (user: User) => {
    await new Promise(resolve => setTimeout(resolve, 500))
    setUsers(prev => prev.map(u =>
      u.id === user.id ? { ...u, is_active: !u.is_active } : u
    ))
  }

  const handleChangeRole = async (user: User, newRole: User['role']) => {
    await new Promise(resolve => setTimeout(resolve, 500))
    setUsers(prev => prev.map(u =>
      u.id === user.id ? { ...u, role: newRole } : u
    ))
    setSelectedUser(null)
  }

  const filteredUsers = users.filter(user => {
    if (searchQuery && !user.username.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !user.email.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !user.full_name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (roleFilter && user.role !== roleFilter) {
      return false
    }
    return true
  })

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const roleLabels = {
    admin: '管理员',
    pm: '产品经理',
    fae: 'FAE',
    user: '普通用户'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
          <p className="text-sm text-gray-500 mt-1">管理平台用户账号和权限</p>
        </div>
      </header>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex gap-4">
            <div className="flex-1 max-w-xs">
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索用户..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm"
                />
              </div>
            </div>

            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="">全部角色</option>
              <option value="admin">管理员</option>
              <option value="user">普通用户</option>
              <option value="pm">产品经理</option>
              <option value="fae">FAE</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="animate-pulse bg-white rounded-lg h-20" />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">练习</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均分</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">最后登录</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredUsers.map(user => (
                  <tr key={user.id} className={!user.is_active ? 'bg-gray-50 opacity-60' : ''}>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center text-primary font-medium">
                          {user.username[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{user.full_name || user.username}</p>
                          <p className="text-sm text-gray-500">@{user.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`
                        px-2 py-1 text-xs font-medium rounded
                        ${user.role === 'admin' ? 'bg-red/10 text-red' :
                          user.role === 'pm' ? 'bg-purple/10 text-purple' :
                          user.role === 'fae' ? 'bg-blue/10 text-blue' :
                          'bg-gray-100 text-gray-600'}
                      `}>
                        {roleLabels[user.role]}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{user.total_sessions}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{user.avg_score}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{formatDate(user.last_login)}</td>
                    <td className="px-6 py-4">
                      <span className={`
                        px-2 py-1 text-xs font-medium rounded
                        ${user.is_active ? 'bg-success/10 text-success' : 'bg-gray-100 text-gray-500'}
                      `}>
                        {user.is_active ? '启用' : '禁用'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setSelectedUser(user)}
                          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                          title="编辑"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleToggleActive(user)}
                          className={`
                            p-2 rounded-lg
                            ${user.is_active ? 'text-red-500 hover:bg-red-50' : 'text-success hover:bg-success/10'}
                          `}
                          title={user.is_active ? '禁用' : '启用'}
                        >
                          {user.is_active ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Edit Modal */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => setSelectedUser(null)} />
          <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">编辑用户 - @{selectedUser.username}</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
                <select
                  value={selectedUser.role}
                  onChange={(e) => handleChangeRole(selectedUser, e.target.value as User['role'])}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="user">普通用户</option>
                  <option value="admin">管理员</option>
                  <option value="pm">产品经理</option>
                  <option value="fae">FAE</option>
                </select>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">邮箱: {selectedUser.email}</p>
                <p className="text-sm text-gray-500">注册时间: {formatDate(selectedUser.created_at)}</p>
                <p className="text-sm text-gray-500">练习次数: {selectedUser.total_sessions}</p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setSelectedUser(null)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserManagementPage