/**
 * BriefListPage - 行业简报（v2：真实新闻 + 订阅）
 *
 * - 订阅管理：选行业 + 关键词
 * - 今日简报：按行业分组，显示真实新闻（带 URL）
 * - 历史简报：分页
 * - 手动刷新
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, {
  BriefSubscription, BriefSubscriptionsUpdate, BriefSummary,
  INDUSTRY_OPTIONS,
} from '../../api/briefs'

type Tab = 'today' | 'history' | 'subs'

const BriefListPage = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('today')
  const [briefs, setBriefs] = useState<BriefSummary[]>([])
  const [todayByIndustry, setTodayByIndustry] = useState<Record<string, BriefSummary[]>>({})
  const [todayDate, setTodayDate] = useState<string>('')
  const [subscriptions, setSubscriptions] = useState<BriefSubscription[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Generate form
  const [industry, setIndustry] = useState('')
  const [keywords, setKeywords] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [subsDraft, setSubsDraft] = useState<BriefSubscription[]>([])
  const [subsSaving, setSubsSaving] = useState(false)
  const [subsMsg, setSubsMsg] = useState<string | null>(null)

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [hist, today, subs] = await Promise.all([
        api.listBriefs(),
        api.getToday().catch(() => ({ date: '', industries: {} })),
        api.getSubscriptions().catch(() => ({ subscriptions: [] })),
      ])
      setBriefs(hist)
      setTodayByIndustry(today.industries || {})
      setTodayDate(today.date || '')
      setSubscriptions(subs.subscriptions || [])
      setSubsDraft(subs.subscriptions || [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || '加载简报失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!industry.trim()) {
      setGenerateError('请选择或输入行业')
      return
    }
    setIsGenerating(true)
    setGenerateError(null)
    try {
      const detail = await api.generateBrief({
        industry: industry.trim(),
        keywords: keywords.trim() || undefined,
      })
      navigate(`/briefs/${detail.id}`)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '生成失败'
      setGenerateError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await api.refreshBriefs()
      await loadAll()
    } catch (e: any) {
      alert('刷新失败：' + (e?.response?.data?.detail || e?.message))
    } finally {
      setIsRefreshing(false)
    }
  }

  // 订阅管理
  const toggleSubsIndustry = (ind: string) => {
    setSubsDraft((prev) => {
      const exists = prev.find((s) => s.industry === ind)
      if (exists) return prev.filter((s) => s.industry !== ind)
      return [...prev, { industry: ind, keywords: '' }]
    })
  }
  const setSubsKeywords = (ind: string, kw: string) => {
    setSubsDraft((prev) =>
      prev.map((s) => s.industry === ind ? { ...s, keywords: kw } : s)
    )
  }
  const saveSubscriptions = async () => {
    setSubsSaving(true)
    setSubsMsg(null)
    try {
      const result = await api.updateSubscriptions({ subscriptions: subsDraft })
      setSubscriptions(result.subscriptions)
      setSubsMsg('✅ 已保存。每日 8:30 后台会自动抓取最新新闻。')
    } catch (e: any) {
      setSubsMsg('❌ 保存失败：' + (e?.response?.data?.detail || e?.message))
    } finally {
      setSubsSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这份简报吗？')) return
    try {
      await api.deleteBrief(id)
      setBriefs((prev) => prev.filter((b) => b.id !== id))
    } catch (e: any) {
      alert(`删除失败：${e?.message || 'unknown'}`)
    }
  }

  const formatDate = (iso: string) => {
    if (!iso) return ''
    try { return new Date(iso).toLocaleString('zh-CN', { hour12: false }) }
    catch { return iso }
  }

  const totalToday = Object.values(todayByIndustry).reduce((s, l) => s + l.length, 0)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">行业简报</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              每日真实新闻推送（Google News RSS + 36kr/虎嗅/IT之家）
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="px-3 py-1.5 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              {isRefreshing ? '抓取中...' : '🔄 立即刷新'}
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md"
            >
              ← 返回
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Tabs */}
        <div className="flex gap-2 border-b border-gray-200">
          {([
            { key: 'today',   label: `今日 (${totalToday})` },
            { key: 'history', label: `历史 (${briefs.length})` },
            { key: 'subs',    label: `我的订阅 (${subsDraft.length})` },
          ] as { key: Tab; label: string }[]).map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === t.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Disclaimer — 真实新闻≠LLM幻觉 */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
          ⚠️ 简报内容来自 Google News RSS 等公共源，<b>由 AI 摘要</b>，请务必点开原文链接核实。每条新闻含 L1-L4 来源分级。
        </div>

        {isLoading && (
          <div className="bg-white rounded-xl shadow-sm p-10 text-center text-gray-400">
            加载中...
          </div>
        )}

        {/* ============== 今日 ============== */}
        {!isLoading && activeTab === 'today' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl shadow-sm p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-1">
                📅 今日简报（{todayDate}）
              </h2>
              <p className="text-xs text-gray-500">
                按你订阅的行业聚合，每行业 1-N 份
              </p>
            </div>

            {totalToday === 0 && (
              <div className="bg-white rounded-xl shadow-sm p-10 text-center">
                <p className="text-gray-600 mb-3">今日还没有简报</p>
                <p className="text-sm text-gray-400 mb-4">
                  在「我的订阅」里选几个行业，点「立即刷新」即可拉取。
                </p>
                <button
                  onClick={() => setActiveTab('subs')}
                  className="px-4 py-2 bg-primary text-white rounded-lg"
                >
                  去订阅
                </button>
              </div>
            )}

            {Object.entries(todayByIndustry).map(([ind, list]) => (
              <div key={ind} className="bg-white rounded-xl shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-sm">
                      {ind}
                    </span>
                    <span className="text-xs text-gray-400 font-normal">{list.length} 份</span>
                  </h3>
                </div>
                <div className="space-y-2">
                  {list.map((b) => (
                    <Link
                      key={b.id}
                      to={`/briefs/${b.id}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="text-sm font-medium text-gray-900">{b.title}</div>
                      <div className="mt-1 text-xs text-gray-500">
                        {b.item_count} 条新闻 · {formatDate(b.created_at)}
                        {b.keywords && ` · 关键词: ${b.keywords}`}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ============== 历史 ============== */}
        {!isLoading && activeTab === 'history' && (
          <div className="space-y-3">
            {error && (
              <div className="bg-red-50 rounded-xl p-4 text-red-600 text-sm">{error}</div>
            )}
            {briefs.length === 0 && (
              <div className="bg-white rounded-xl shadow-sm p-10 text-center text-gray-400">
                还没有简报。在「我的订阅」里订阅几个行业后点「立即刷新」即可。
              </div>
            )}
            {briefs.map((b) => (
              <div
                key={b.id}
                className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between"
              >
                <Link to={`/briefs/${b.id}`} className="flex-1 min-w-0 cursor-pointer">
                  <div className="font-semibold text-gray-900 truncate">{b.title}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    {b.industry && (
                      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">
                        {b.industry}
                      </span>
                    )}
                    <span>· {b.item_count} 条新闻 · {formatDate(b.created_at)}</span>
                  </div>
                </Link>
                <button
                  onClick={() => handleDelete(b.id)}
                  className="ml-3 text-xs text-red-500 hover:text-red-700"
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ============== 我的订阅 ============== */}
        {!isLoading && activeTab === 'subs' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl shadow-sm p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-2">
                订阅行业（每日 8:30 自动推送）
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                勾选要订阅的行业，可选填关键词更精准。
                后台每日 8:30 拉近 48 小时新闻；点「立即刷新」可手动拉。
              </p>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {INDUSTRY_OPTIONS.map((ind) => {
                  const sel = subsDraft.find((s) => s.industry === ind)
                  return (
                    <button
                      key={ind}
                      onClick={() => toggleSubsIndustry(ind)}
                      className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
                        sel
                          ? 'border-primary bg-primary/5 text-primary font-medium'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}
                    >
                      {sel ? '✓ ' : '+ '}{ind}
                    </button>
                  )
                })}
              </div>

              {subsDraft.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h3 className="text-sm font-medium text-gray-700">关键词（可选，让推送更精准）</h3>
                  {subsDraft.map((s) => (
                    <div key={s.industry} className="flex items-center gap-2">
                      <span className="w-24 text-sm text-gray-700 truncate">{s.industry}</span>
                      <input
                        type="text"
                        value={s.keywords}
                        onChange={(e) => setSubsKeywords(s.industry, e.target.value)}
                        placeholder="比如：SaaS CRM 转型 数字化"
                        className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                      />
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={saveSubscriptions}
                  disabled={subsSaving}
                  className="px-5 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
                >
                  {subsSaving ? '保存中...' : '保存订阅'}
                </button>
                {subsMsg && (
                  <span className="text-sm text-gray-600">{subsMsg}</span>
                )}
              </div>
            </div>

            {/* 一次性生成（兼容旧版 UI） */}
            <details className="bg-white rounded-xl shadow-sm p-5">
              <summary className="cursor-pointer text-sm text-gray-700 font-medium">
                ⚙️ 一次性生成（不订阅）
              </summary>
              <div className="mt-3 flex flex-col sm:flex-row gap-2">
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">选择行业</option>
                  {INDUSTRY_OPTIONS.map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="关键词（可选）"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                />
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="px-5 py-2 bg-secondary text-white rounded-lg hover:bg-secondary/90 disabled:opacity-50 whitespace-nowrap"
                >
                  {isGenerating ? '生成中...' : '生成'}
                </button>
              </div>
              {generateError && (
                <p className="mt-2 text-sm text-red-600">{generateError}</p>
              )}
            </details>
          </div>
        )}
      </main>
    </div>
  )
}

export default BriefListPage
