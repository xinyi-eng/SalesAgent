/**
 * DataExportPage - Data export and report generation
 *
 * Features:
 * - Export practice data to CSV/PDF
 * - Generate batch reports
 * - Schedule automated exports
 * - Export user progress reports
 *
 * Story: 4.4 数据导出
 */
import { useState } from 'react'

interface ExportJob {
  id: string
  type: 'practice_history' | 'user_progress' | 'scenario_analytics' | 'system_stats'
  format: 'csv' | 'pdf' | 'xlsx'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
  completed_at?: string
  download_url?: string
}

const DataExportPage = () => {
  const [exportJobs, setExportJobs] = useState<ExportJob[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [selectedType, setSelectedType] = useState<ExportJob['type']>('practice_history')
  const [selectedFormat, setSelectedFormat] = useState<ExportJob['format']>('csv')
  const [dateRange, setDateRange] = useState({ start: '', end: '' })

  const exportTypes = [
    { value: 'practice_history', label: '练习历史记录', description: '导出所有用户的练习历史' },
    { value: 'user_progress', label: '用户进步报告', description: '导出用户的能力提升情况' },
    { value: 'scenario_analytics', label: '场景分析', description: '导出各场景的使用统计数据' },
    { value: 'system_stats', label: '系统统计', description: '导出平台运营统计数据' }
  ]

  const formats = [
    { value: 'csv', label: 'CSV', description: '适合数据分析' },
    { value: 'xlsx', label: 'Excel', description: '适合进一步处理' },
    { value: 'pdf', label: 'PDF', description: '适合阅读和打印' }
  ]

  const handleCreateExport = async () => {
    setIsCreating(true)
    await new Promise(resolve => setTimeout(resolve, 1000))

    const newJob: ExportJob = {
      id: `export-${Date.now()}`,
      type: selectedType,
      format: selectedFormat,
      status: 'processing',
      progress: 0,
      created_at: new Date().toISOString()
    }

    setExportJobs(prev => [newJob, ...prev])

    // Simulate progress
    const interval = setInterval(() => {
      setExportJobs(prev => prev.map(job => {
        if (job.id === newJob.id && job.progress < 100) {
          const newProgress = Math.min(job.progress + Math.random() * 30, 100)
          return {
            ...job,
            progress: newProgress,
            status: newProgress >= 100 ? 'completed' : 'processing',
            completed_at: newProgress >= 100 ? new Date().toISOString() : undefined,
            download_url: newProgress >= 100 ? '#' : undefined
          }
        }
        return job
      }))
    }, 500)

    setTimeout(() => clearInterval(interval), 5000)
    setIsCreating(false)
  }

  const handleDownload = (job: ExportJob) => {
    if (job.download_url) {
      alert(`下载文件: ${job.type}.${job.format}`)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const statusLabels = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">数据导出</h1>
          <p className="text-sm text-gray-500 mt-1">导出平台数据和生成报告</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid md:grid-cols-2 gap-6">
          {/* Create Export */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">创建新导出</h2>

            {/* Export Type */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">导出类型</label>
              <div className="space-y-2">
                {exportTypes.map(type => (
                  <button
                    key={type.value}
                    onClick={() => setSelectedType(type.value as ExportJob['type'])}
                    className={`
                      w-full text-left p-3 rounded-lg border-2 transition-all
                      ${selectedType === type.value
                        ? 'border-primary bg-primary/5'
                        : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                  >
                    <p className="font-medium text-gray-900">{type.label}</p>
                    <p className="text-sm text-gray-500">{type.description}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Format */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">导出格式</label>
              <div className="flex gap-2">
                {formats.map(format => (
                  <button
                    key={format.value}
                    onClick={() => setSelectedFormat(format.value as ExportJob['format'])}
                    className={`
                      flex-1 p-3 rounded-lg border-2 transition-all text-center
                      ${selectedFormat === format.value
                        ? 'border-primary bg-primary/5'
                        : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                  >
                    <p className="font-medium text-gray-900">{format.label}</p>
                    <p className="text-xs text-gray-500">{format.description}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Date Range */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">日期范围（可选）</label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={dateRange.start}
                  onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="开始日期"
                />
                <span className="self-center text-gray-400">至</span>
                <input
                  type="date"
                  value={dateRange.end}
                  onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="结束日期"
                />
              </div>
            </div>

            <button
              onClick={handleCreateExport}
              disabled={isCreating}
              className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isCreating ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  创建中...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  创建导出任务
                </>
              )}
            </button>
          </div>

          {/* Export History */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">导出历史</h2>

            {exportJobs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>暂无导出记录</p>
              </div>
            ) : (
              <div className="space-y-3">
                {exportJobs.map(job => (
                  <div key={job.id} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-medium text-gray-900">
                          {exportTypes.find(t => t.value === job.type)?.label}
                        </p>
                        <p className="text-sm text-gray-500">
                          {job.format.toUpperCase()} · {formatDate(job.created_at)}
                        </p>
                      </div>
                      <span className={`
                        px-2 py-1 text-xs font-medium rounded
                        ${job.status === 'completed' ? 'bg-success/10 text-success' :
                          job.status === 'processing' ? 'bg-primary/10 text-primary' :
                          job.status === 'failed' ? 'bg-red/10 text-red' :
                          'bg-gray-100 text-gray-500'}
                      `}>
                        {statusLabels[job.status]}
                      </span>
                    </div>

                    {job.status === 'processing' && (
                      <div className="mb-2">
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all"
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{Math.round(job.progress)}%</p>
                      </div>
                    )}

                    {job.status === 'completed' && (
                      <button
                        onClick={() => handleDownload(job)}
                        className="w-full py-2 bg-success/10 text-success rounded-lg hover:bg-success/20 text-sm font-medium"
                      >
                        下载文件
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default DataExportPage