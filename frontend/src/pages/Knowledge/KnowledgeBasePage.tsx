/**
 * KnowledgeBasePage - RAG knowledge base management
 *
 * Features:
 * - Document list and status
 * - Knowledge search
 * - SPIN question generation
 * - Integration with practice scenarios
 *
 * Story: Knowledge Base Integration
 */
import { useState, useEffect } from 'react'
import api from '../../api/knowledge'
import type { KnowledgeStats, KnowledgeDocument, SearchResult, SpinQuestions } from '../../api/knowledge'

const KnowledgeBasePage = () => {
  const [activeTab, setActiveTab] = useState('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  // Documents state
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isIngesting, setIsIngesting] = useState(false)

  // SPIN form state
  const [spinIndustry, setSpinIndustry] = useState('')
  const [spinScale, setSpinScale] = useState('')
  const [spinPainPoints, setSpinPainPoints] = useState('')
  const [spinQuestions, setSpinQuestions] = useState<SpinQuestions | null>(null)
  const [isGeneratingSpin, setIsGeneratingSpin] = useState(false)
  const [spinError, setSpinError] = useState<string | null>(null)

  const tabs = [
    { key: 'search', label: '知识检索' },
    { key: 'documents', label: '文档管理' },
    { key: 'spin', label: 'SPIN问题生成' }
  ]

  // Load initial data — 失败时显示错误状态，不填充假数据
  const loadData = async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const [docsData, statsData] = await Promise.all([
        api.getDocuments(),
        api.getStats()
      ])
      setDocuments(docsData || [])
      setStats(statsData)
    } catch (error: any) {
      console.error('Failed to load knowledge base data:', error)
      setLoadError(
        error?.response?.data?.detail || error?.message || '加载知识库失败'
      )
      setDocuments([])
      setStats(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'documents') {
      loadData()
    }
  }, [activeTab])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setIsSearching(true)
    setSearchError(null)
    try {
      const response = await api.search(searchQuery, 5)
      setSearchResults(response.results || [])
    } catch (error: any) {
      console.error('Search failed:', error)
      setSearchResults([])  // 失败时不返回任何伪造结果
      setSearchError(
        error?.response?.data?.detail || error?.message || '搜索失败'
      )
    } finally {
      setIsSearching(false)
    }
  }

  const handleIngestAll = async () => {
    setIsIngesting(true)
    try {
      const response = await api.ingestAll()
      // Reload data after ingest
      await loadData()
      alert(`知识库更新完成！共处理 ${response.total} 个文档`)
    } catch (error: any) {
      console.error('Ingest failed:', error)
      alert('更新失败：' + (error?.response?.data?.detail || error?.message || '未知错误'))
    } finally {
      setIsIngesting(false)
    }
  }

  const handleGenerateSpin = async () => {
    if (!spinIndustry || !spinScale || !spinPainPoints) {
      alert('请填写完整的客户信息')
      return
    }

    setIsGeneratingSpin(true)
    setSpinError(null)
    try {
      const painPointsList = spinPainPoints.split(',').map(p => p.trim()).filter(Boolean)
      const response = await api.generateSpinQuestions({
        customer_industry: spinIndustry,
        customer_scale: spinScale,
        pain_points: painPointsList
      })
      setSpinQuestions(response)
    } catch (error: any) {
      console.error('SPIN generation failed:', error)
      setSpinQuestions(null)
      setSpinError(
        error?.response?.data?.detail || error?.message || 'SPIN 生成失败'
      )
    } finally {
      setIsGeneratingSpin(false)
    }
  }

  const renderSearchTab = () => (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="输入关键词搜索知识库..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          onClick={handleSearch}
          disabled={isSearching}
          className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
        >
          {isSearching ? '搜索中...' : '搜索'}
        </button>
      </div>

      {searchError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          搜索失败：{searchError}
          <button onClick={handleSearch} className="ml-3 underline">重试</button>
        </div>
      ) : searchResults.length > 0 ? (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">找到 {searchResults.length} 条相关知识</p>
          {searchResults.map((result) => (
            <div key={result.id} className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <span className={`px-2 py-1 text-xs font-medium rounded ${
                  result.metadata?.category === 'spin' ? 'bg-blue/10 text-blue' :
                  result.metadata?.category === 'solution_selling' ? 'bg-green/10 text-green' :
                  'bg-purple/10 text-purple'
                }`}>
                  {result.source}
                </span>
                <span className="text-xs text-gray-400">
                  相似度: {Math.round(result.score * 100)}%
                </span>
              </div>
              <p className="text-gray-700 text-sm leading-relaxed">{result.text}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p>输入关键词开始搜索知识库</p>
        </div>
      )}
    </div>
  )

  const renderDocumentsTab = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">知识库文档</h3>
        <button
          onClick={handleIngestAll}
          disabled={isIngesting}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
        >
          {isIngesting ? (
            <>
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              更新中...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              同步原始数据
            </>
          )}
        </button>
      </div>

      {loadError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          加载失败：{loadError}
          <button onClick={loadData} className="ml-3 underline">重试</button>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>暂无文档，请点击"同步原始数据"导入PDF文档</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {documents.map(doc => (
            <div key={doc.id} className="bg-white p-4 rounded-lg border border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  doc.category === 'spin' ? 'bg-blue/10 text-blue' :
                  doc.category === 'strategic_marketing' ? 'bg-green/10 text-green' :
                  'bg-purple/10 text-purple'
                }`}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-gray-900">{doc.name}</p>
                  <p className="text-sm text-gray-500">{doc.chunk_count} 个知识片段</p>
                </div>
              </div>
              <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                doc.status === 'completed' ? 'bg-success/10 text-success' :
                doc.status === 'processing' ? 'bg-primary/10 text-primary' :
                'bg-gray-100 text-gray-500'
              }`}>
                {doc.status === 'completed' ? '已索引' : doc.status === 'processing' ? '处理中' : '待处理'}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-2">知识库统计</h4>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-primary">{stats?.total_documents || documents.length}</p>
            <p className="text-xs text-gray-500">文档总数</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-primary">{stats?.total_chunks || documents.reduce((acc, d) => acc + d.chunk_count, 0)}</p>
            <p className="text-xs text-gray-500">知识片段</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-success">{Object.keys(stats?.documents_by_category || {}).length || 3}</p>
            <p className="text-xs text-gray-500">已分类</p>
          </div>
        </div>
      </div>
    </div>
  )

  const renderSpinTab = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">客户背景信息</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">客户行业</label>
            <input
              type="text"
              value={spinIndustry}
              onChange={(e) => setSpinIndustry(e.target.value)}
              placeholder="例如：制造业、互联网、金融"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">公司规模</label>
            <input
              type="text"
              value={spinScale}
              onChange={(e) => setSpinScale(e.target.value)}
              placeholder="例如：50-100人、上市公司、初创企业"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">痛点（逗号分隔）</label>
          <textarea
            value={spinPainPoints}
            onChange={(e) => setSpinPainPoints(e.target.value)}
            placeholder="例如：成单周期长、客户转化率低、销售团队能力参差不齐"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            rows={3}
          />
        </div>
        <button
          onClick={handleGenerateSpin}
          disabled={isGeneratingSpin}
          className="mt-4 w-full py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {isGeneratingSpin ? (
            <>
              <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              生成中...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              生成SPIN问题
            </>
          )}
        </button>
      </div>

      {spinError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          SPIN 生成失败：{spinError}
          <button onClick={handleGenerateSpin} className="ml-3 underline">重试</button>
        </div>
      )}

      {spinQuestions && (
        <div className="space-y-4">
          {[
            { title: 'Situation（现状）', questions: spinQuestions.situation_questions, color: 'blue', icon: '📋' },
            { title: 'Problem（问题）', questions: spinQuestions.problem_questions, color: 'orange', icon: '❓' },
            { title: 'Implication（暗示）', questions: spinQuestions.implication_questions, color: 'red', icon: '⚠️' },
            { title: 'Need-Payoff（价值）', questions: spinQuestions.need_payoff_questions, color: 'green', icon: '💰' }
          ].map(category => (
            <div key={category.title} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className={`px-4 py-3 bg-${category.color}-50 border-b border-${category.color}-100`}>
                <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                  <span>{category.icon}</span>
                  {category.title}
                </h4>
              </div>
              <div className="p-4 space-y-2">
                {category.questions.map((q, i) => (
                  <div key={i} className="flex items-start gap-3 p-2 rounded hover:bg-gray-50">
                    <span className={`w-6 h-6 rounded-full bg-${category.color}-100 text-${category.color}-600 text-xs flex items-center justify-center flex-shrink-0`}>
                      {i + 1}
                    </span>
                    <span className="text-gray-700">{q}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-900 mb-2">使用的知识库内容</h5>
            <ul className="space-y-1">
              {spinQuestions.context_used.map((ctx, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                  {ctx}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">知识库</h1>
          <p className="text-sm text-gray-500 mt-1">RAG检索增强生成 - 基于销售专业文献</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-primary text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          {activeTab === 'search' && renderSearchTab()}
          {activeTab === 'documents' && renderDocumentsTab()}
          {activeTab === 'spin' && renderSpinTab()}
        </div>
      </main>
    </div>
  )
}

export default KnowledgeBasePage