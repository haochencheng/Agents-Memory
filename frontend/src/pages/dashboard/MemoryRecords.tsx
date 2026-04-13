import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { type SearchResultItem, useErrors, useRules, useSearchResults } from '@/api/useMemory'
import { useWikiGraph } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import WikiTopicPreviewLink from '@/components/WikiTopicPreviewLink'
import { formatDate } from '@/lib/utils'

type Tab = 'errors' | 'rules'

function conceptTarget(concept: {
  id: string
  primary_topic?: string
}) {
  if (concept.primary_topic?.trim()) {
    return `/wiki/${encodeURIComponent(concept.primary_topic)}`
  }
  return `/wiki/graph?node=${encodeURIComponent(concept.id)}`
}

function conceptPreview(graph: {
  nodes?: Array<{ id: string; title: string; node_type?: string; project?: string; primary_topic?: string; topic_count?: number }>
  edges?: Array<{ source: string; target: string }>
} | undefined, conceptId: string) {
  const nodes = graph?.nodes ?? []
  const edges = graph?.edges ?? []
  const node = nodes.find(item => item.id === conceptId)
  if (!node) return null

  const nodeMap = new Map(nodes.map(item => [item.id, item]))
  const neighborPages: Array<{ topic: string; title: string }> = []
  const seenTopics = new Set<string>()

  const pushPage = (topic?: string, title?: string) => {
    if (!topic?.trim() || seenTopics.has(topic)) return
    seenTopics.add(topic)
    neighborPages.push({ topic, title: title || topic })
  }

  pushPage(node.primary_topic, node.title)
  edges.forEach(edge => {
    if (edge.source !== conceptId && edge.target !== conceptId) return
    const neighborId = edge.source === conceptId ? edge.target : edge.source
    const neighbor = nodeMap.get(neighborId)
    pushPage(neighbor?.primary_topic, neighbor?.title)
  })

  return {
    node,
    pages: neighborPages.slice(0, 4),
  }
}

function searchResultTarget(result: SearchResultItem) {
  if (result.type === 'wiki') {
    return `/wiki/${encodeURIComponent(result.id)}`
  }
  if (result.type === 'workflow') {
    return `/workflow/${encodeURIComponent(result.id)}`
  }
  return `/memory/errors/${encodeURIComponent(result.id)}`
}

export default function MemoryRecords() {
  const [tab, setTab] = useState<Tab>('errors')
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [errorPage, setErrorPage] = useState(1)
  const navigate = useNavigate()
  const { data: errors, isLoading: errLoading, error: errError } = useErrors({ page: errorPage, pageSize: 20 })
  const { data: rules, isLoading: rulesLoading, error: rulesError } = useRules()
  const { data: searchData, isLoading: searchLoading } = useSearchResults(query)
  const { data: graphData } = useWikiGraph()

  const isLoading = tab === 'errors' ? errLoading : rulesLoading
  const err = tab === 'errors' ? errError : rulesError

  const submitSearch = () => {
    setQuery(queryDraft.trim())
  }

  return (
    <div className="space-y-6" data-testid="memory-records-page">
      <h1 className="page-title">记忆记录</h1>

      <div className="bg-white rounded-xl border border-gray-100 p-4 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="section-title">统一搜索</h2>
            <p className="text-sm text-gray-500">搜索 wiki、workflow 和错误记录，并显示 graph rerank 原因。</p>
          </div>
          {query.trim() && (
            <span className="text-xs text-gray-400">
              {searchLoading ? '搜索中...' : `${searchData?.total ?? 0} 条结果`}
            </span>
          )}
        </div>
        <form
          className="flex max-w-4xl items-stretch gap-3"
          onSubmit={event => {
            event.preventDefault()
            submitSearch()
          }}
        >
          <input
            value={queryDraft}
            onChange={event => setQueryDraft(event.target.value)}
            placeholder="例如：jwt、auth refresh、billing recharge"
            className="h-12 min-w-0 flex-1 rounded-xl border border-gray-200 px-4 text-sm outline-none focus:border-blue-400"
            data-testid="memory-search-input"
          />
          <button
            type="submit"
            className="h-12 rounded-xl bg-blue-600 px-5 text-sm font-medium text-white transition hover:bg-blue-700"
            data-testid="memory-search-submit"
          >
            搜索
          </button>
        </form>
        {query.trim() && !searchLoading && (
          <div className="space-y-3">
            {(searchData?.results ?? []).length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-400 text-center">
                没有找到匹配结果
              </div>
            ) : (
              (searchData?.results ?? []).slice(0, 6).map(result => (
                <div
                  key={`${result.type}:${result.id}`}
                  className="rounded-xl border border-gray-100 p-4 transition hover:border-blue-200 hover:shadow-sm cursor-pointer"
                  onClick={() => navigate(searchResultTarget(result))}
                  onKeyDown={event => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      navigate(searchResultTarget(result))
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="badge badge-blue">{result.type}</span>
                        <p className="text-sm font-medium text-gray-800">{result.title}</p>
                      </div>
                      {result.snippet && <p className="text-xs text-gray-500 mt-2 line-clamp-2">{result.snippet}</p>}
                      {(result.rerank_reasons ?? []).length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {(result.rerank_reasons ?? []).map(reason => (
                            <span key={reason} className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-1 text-xs text-amber-700 border border-amber-200">
                              {reason}
                            </span>
                          ))}
                        </div>
                      )}
                      {(result.matched_concepts ?? []).length > 0 && (
                        <div className="mt-3">
                          <div className="text-xs font-medium text-slate-500 mb-2">命中的图谱概念</div>
                          <div className="flex flex-wrap gap-2">
                            {(result.matched_concepts ?? []).map(concept => (
                              <div
                                key={`${result.id}-${concept.id}`}
                                className="relative group"
                                onClick={event => event.stopPropagation()}
                              >
                                <Link
                                  to={conceptTarget(concept)}
                                  className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs text-blue-700 hover:border-blue-300 hover:bg-blue-100"
                                >
                                  <span>{concept.title}</span>
                                  <span className="text-[11px] text-blue-500">
                                    {concept.primary_topic ? 'wiki' : 'graph'}
                                  </span>
                                </Link>

                                {(() => {
                                  const preview = conceptPreview(graphData, concept.id)
                                  if (!preview) return null
                                  return (
                                    <div className="pointer-events-none invisible absolute left-0 top-full z-20 mt-2 w-72 rounded-xl border border-slate-200 bg-white p-4 text-left shadow-xl transition duration-150 group-hover:visible group-hover:pointer-events-auto group-focus-within:visible group-focus-within:pointer-events-auto">
                                      <div className="flex items-start justify-between gap-3">
                                        <div>
                                          <div className="text-sm font-semibold text-slate-900">{preview.node.title}</div>
                                          <div className="mt-1 text-xs text-slate-500">
                                            {(preview.node.node_type || 'entity')} · {preview.node.project || 'unassigned'}
                                          </div>
                                        </div>
                                        <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
                                          {preview.node.topic_count ?? 0} pages
                                        </span>
                                      </div>

                                      <div className="mt-3">
                                        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">关联页面</div>
                                        <div className="mt-2 space-y-2">
                                          {preview.pages.length === 0 ? (
                                            <div className="text-xs text-slate-400">当前概念还没有可跳转的 wiki 页面。</div>
                                          ) : (
                                            preview.pages.map(page => (
                                              <WikiTopicPreviewLink
                                                key={`${concept.id}-${page.topic}`}
                                                topic={page.topic}
                                                title={page.title}
                                              />
                                            ))
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  )
                                })()}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-xs text-gray-400">score {result.score.toFixed(2)}</div>
                      {(result.rerank_boost ?? 0) > 0 && (
                        <div className="text-xs text-emerald-600 mt-1">+{result.rerank_boost?.toFixed(2)} graph</div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['errors', 'rules'] as Tab[]).map(t => (
          <button
            key={t}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setTab(t)}
          >
            {t === 'errors' ? '错误记录' : '规则'}
          </button>
        ))}
      </div>

      {isLoading && <LoadingSpinner text="加载中..." />}
      {err && <ErrorAlert message="数据加载失败" />}

      {/* Errors */}
      {tab === 'errors' && !isLoading && !err && (
        <div className="space-y-3">
          {(!errors?.errors || errors.errors.length === 0) ? (
            <div className="bg-white rounded-xl border p-10 text-center text-gray-400">暂无错误记录</div>
          ) : (
            <>
              <div className="flex items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3 text-sm text-gray-500" data-testid="errors-pagination-summary">
                <span>当前显示错误记录</span>
                <span>第 {errors?.page ?? 1} / {errors?.total_pages ?? 1} 页，每页 {errors?.page_size ?? 20} 条</span>
              </div>
              {errors.errors.map((e, i) => (
                <Link
                  key={i}
                  to={`/memory/errors/${encodeURIComponent(e.id)}`}
                  className="block bg-white rounded-xl border border-gray-100 p-4 transition hover:border-blue-200 hover:shadow-sm"
                  data-testid="error-record"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{e.title}</p>
                      {e.project && <span className="badge badge-blue mt-1">{e.project}</span>}
                    </div>
                    <span className="text-xs text-gray-400 flex-shrink-0">{formatDate(e.created_at)}</span>
                  </div>
                </Link>
              ))}
              {(errors?.total_pages ?? 0) > 1 && (
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    className="btn btn-outline"
                    disabled={(errors?.page ?? 1) <= 1}
                    onClick={() => setErrorPage(page => Math.max(1, page - 1))}
                  >
                    上一页
                  </button>
                  {Array.from({ length: errors?.total_pages ?? 0 }, (_, index) => index + 1).slice(
                    Math.max(0, (errors?.page ?? 1) - 3),
                    Math.max(5, Math.min(errors?.total_pages ?? 0, (errors?.page ?? 1) + 2)),
                  ).map(page => (
                    <button
                      key={page}
                      type="button"
                      className={`rounded-lg px-3 py-2 text-sm ${page === (errors?.page ?? 1) ? 'bg-blue-600 text-white' : 'border border-gray-200 bg-white text-gray-600'}`}
                      onClick={() => setErrorPage(page)}
                    >
                      {page}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="btn btn-outline"
                    disabled={(errors?.page ?? 1) >= (errors?.total_pages ?? 1)}
                    onClick={() => setErrorPage(page => Math.min(errors?.total_pages ?? page, page + 1))}
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Rules */}
      {tab === 'rules' && !isLoading && !err && (
        <div className="space-y-3">
          {(!rules?.rules || rules.rules.length === 0) ? (
            <div className="bg-white rounded-xl border p-10 text-center text-gray-400">暂无规则</div>
          ) : (
            rules.rules.map((r, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid="rule-record">
                <p className="text-sm text-gray-800 font-mono">{r.content}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
