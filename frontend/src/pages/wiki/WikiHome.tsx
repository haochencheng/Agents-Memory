import { useState } from 'react'
import { useWikiList } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import WikiCard from '@/components/WikiCard'

export default function WikiHome() {
  const { data: topics, isLoading, error } = useWikiList()
  const [query, setQuery] = useState('')

  const filtered = (topics?.topics ?? []).filter(t =>
    !query || t.topic.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="space-y-6" data-testid="wiki-home-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Wiki 知识库</h1>
        <span className="text-sm text-gray-500">{topics?.topics?.length ?? 0} 篇</span>
      </div>

      {/* Search */}
      <div className="relative">
        <input
          className="input w-full pl-9"
          placeholder="搜索 Wiki 主题..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          data-testid="wiki-search-input"
        />
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
      </div>

      {isLoading && <LoadingSpinner text="加载 Wiki 列表..." />}
      {error && <ErrorAlert message="Wiki 列表加载失败" />}

      {!isLoading && !error && (
        <>
          {filtered.length === 0 ? (
            <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
              {query ? `未找到匹配 "${query}" 的页面` : '暂无 Wiki 页面'}
            </div>
          ) : (
            <div className="space-y-3">
              {filtered.map(t => (
                <WikiCard key={t.topic} topic={t} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
