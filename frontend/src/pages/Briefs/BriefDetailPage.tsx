/**
 * BriefDetailPage - 简报详情
 *
 * - 一句话总结
 * - L1/L2/L3/L4 分层新闻条目
 * - 关键要点
 * - 导出 PDF
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api, { BriefDetail, BriefItem } from '../../api/briefs'

const BriefDetailPage = () => {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [brief, setBrief] = useState<BriefDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBrief()
  }, [id])

  const loadBrief = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.getBrief(id)
      setBrief(data)
    } catch (e: any) {
      setError(e?.message || '加载失败')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-400">
        加载中...
      </div>
    )
  }

  if (error || !brief) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <button
              onClick={() => navigate('/briefs')}
              className="text-sm text-gray-600 hover:underline"
            >
              ← 返回列表
            </button>
          </div>
        </header>
        <div className="max-w-4xl mx-auto p-8 text-red-600">
          {error || '简报不存在'}
        </div>
      </div>
    )
  }

  const formatDate = (iso: string) => {
    if (!iso) return ''
    try {
      return new Date(iso).toLocaleString('zh-CN', { hour12: false })
    } catch {
      return iso
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <button
              onClick={() => navigate('/briefs')}
              className="text-xs text-gray-500 hover:underline mb-1"
            >
              ← 返回列表
            </button>
            <h1 className="text-xl font-bold text-gray-900 truncate">
              {brief.title}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
              {brief.industry && (
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">
                  {brief.industry}
                </span>
              )}
              <span>{formatDate(brief.created_at)}</span>
              {brief.status && (
                <span
                  className={`px-2 py-0.5 rounded-full ${
                    brief.status === 'ready'
                      ? 'bg-green-50 text-green-700'
                      : 'bg-yellow-50 text-yellow-700'
                  }`}
                >
                  {brief.status === 'ready' ? '就绪' : brief.status}
                </span>
              )}
            </div>
          </div>
          <a
            href={api.pdfUrl(brief.id)}
            target="_blank"
            rel="noreferrer"
            className="ml-3 px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/90"
          >
            导出 PDF
          </a>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {brief.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            <div className="font-semibold mb-1">生成过程中出错：</div>
            <div>{brief.error}</div>
          </div>
        )}

        {/* Summary */}
        {brief.summary && (
          <section className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-500 mb-2">
              简报摘要
            </h2>
            <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
              {brief.summary}
            </p>
          </section>
        )}

        {/* Items */}
        {brief.items && brief.items.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-500 mb-3 px-1">
              行业动态（{brief.items.length} 条）
            </h2>
            <div className="space-y-3">
              {brief.items.map((it, idx) => (
                <BriefItemCard key={idx} item={it} />
              ))}
            </div>
          </section>
        )}

        {/* Key takeaways */}
        {brief.key_takeaways && brief.key_takeaways.length > 0 && (
          <section className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-500 mb-3">
              给销售的要点
            </h2>
            <ul className="space-y-2">
              {brief.key_takeaways.map((t, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-semibold">
                    {idx + 1}
                  </span>
                  <span className="text-gray-800 leading-relaxed">{t}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Empty state */}
        {(!brief.items || brief.items.length === 0) &&
          (!brief.key_takeaways || brief.key_takeaways.length === 0) &&
          !brief.summary && (
            <div className="bg-white rounded-xl shadow-sm p-10 text-center text-gray-400">
              这份简报还没有内容。
            </div>
          )}
      </main>
    </div>
  )
}

const BriefItemCard = ({ item }: { item: BriefItem }) => {
  const colors = api.levelColor(item.source_level)
  const time = item.published_at || item.date
  const formattedTime = (() => {
    if (!time) return ''
    try {
      const d = new Date(time)
      const now = new Date()
      const diffH = (now.getTime() - d.getTime()) / 3600000
      if (diffH < 24) return `${Math.floor(diffH)}小时前`
      return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    } catch { return time }
  })()
  return (
    <article className="bg-white rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-2 mb-2">
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${colors.bg} ${colors.text} flex-shrink-0`}>
          {colors.label}
        </span>
        {formattedTime && (
          <span className="text-[10px] text-gray-400">⏱ {formattedTime}</span>
        )}
        {item.source && (
          <span className="text-[10px] text-gray-400 ml-auto">来源：{item.source}</span>
        )}
      </div>
      <h3 className="font-semibold text-gray-900 leading-snug">
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-primary hover:underline"
          >
            {item.title} <span className="text-xs text-gray-400">↗</span>
          </a>
        ) : (
          item.title
        )}
      </h3>
      {item.summary && (
        <p className="mt-1.5 text-sm text-gray-600 leading-relaxed">
          {item.summary}
        </p>
      )}
      {item.url && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline truncate flex-1"
          >
            🔗 {item.url}
          </a>
        </div>
      )}
    </article>
  )
}

export default BriefDetailPage
