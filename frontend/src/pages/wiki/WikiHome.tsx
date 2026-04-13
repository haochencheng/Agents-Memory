import { type FormEvent, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useWikiList } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import WikiCard from '@/components/WikiCard'

const PAGE_SIZE = 20

function buildPageNumbers(currentPage: number, totalPages: number): number[] {
  const start = Math.max(1, currentPage - 2)
  const end = Math.min(totalPages, currentPage + 2)
  const pages: number[] = []
  for (let page = start; page <= end; page += 1) {
    pages.push(page)
  }
  return pages
}

export default function WikiHome() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') ?? ''
  const initialPage = Number.parseInt(searchParams.get('page') ?? '1', 10)
  const [draftQuery, setDraftQuery] = useState(initialQuery)
  const [query, setQuery] = useState(initialQuery)
  const [page, setPage] = useState(Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1)
  const { data: topics, isLoading, error } = useWikiList({ query, page, pageSize: PAGE_SIZE })
  const pageNumbers = buildPageNumbers(topics?.page ?? page, topics?.total_pages ?? 1)

  useEffect(() => {
    const nextParams = new URLSearchParams()
    if (query.trim()) nextParams.set('q', query.trim())
    if (page > 1) nextParams.set('page', String(page))
    setSearchParams(nextParams, { replace: true })
  }, [page, query, setSearchParams])

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setQuery(draftQuery.trim())
    setPage(1)
  }

  return (
    <div className="space-y-6" data-testid="wiki-home-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Wiki 知识库</h1>
          <p className="mt-1 text-sm text-gray-500">这里是全量 wiki 索引页，用于浏览、检索并进入具体知识页面。</p>
        </div>
        <span className="text-sm text-gray-500">{topics?.total ?? 0} 篇</span>
      </div>

      <form className="flex max-w-4xl flex-col gap-3 sm:flex-row sm:items-stretch" onSubmit={handleSearchSubmit}>
        <div className="relative min-w-0 flex-1">
          <input
            className="input h-12 w-full pl-9"
            placeholder="搜索标题、标签、项目、路径或正文内容..."
            value={draftQuery}
            onChange={e => setDraftQuery(e.target.value)}
            data-testid="wiki-search-input"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
        </div>
        <button type="submit" className="btn h-12 whitespace-nowrap px-5" data-testid="wiki-search-submit">
          搜索
        </button>
      </form>

      {isLoading && <LoadingSpinner text="加载 Wiki 列表..." />}
      {error && <ErrorAlert message="Wiki 列表加载失败" />}

      {!isLoading && !error && (
        <>
          <div className="flex flex-col gap-2 rounded-xl border border-gray-100 bg-white px-4 py-3 text-sm text-gray-500 sm:flex-row sm:items-center sm:justify-between">
            <span>
              {query ? `搜索词: "${query}"` : '当前显示全部 Wiki 页面'}
            </span>
            <span data-testid="wiki-pagination-summary">
              第 {topics?.page ?? 1} / {(topics?.total_pages ?? 0) || 1} 页，每页 {topics?.page_size ?? PAGE_SIZE} 条
            </span>
          </div>

          {(topics?.topics ?? []).length === 0 ? (
            <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
              {query ? `未找到匹配 "${query}" 的页面` : '暂无 Wiki 页面'}
            </div>
          ) : (
            <div className="space-y-3">
              {(topics?.topics ?? []).map(t => (
                <WikiCard key={t.topic} topic={t} />
              ))}
            </div>
          )}

          {(topics?.total_pages ?? 0) > 1 && (
            <div className="flex items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3">
              <button
                type="button"
                className="btn btn-outline"
                disabled={(topics?.page ?? 1) <= 1}
                onClick={() => setPage(current => Math.max(1, current - 1))}
              >
                上一页
              </button>

              <div className="flex items-center gap-2 text-sm text-gray-500" data-testid="wiki-pagination-controls">
                {pageNumbers[0] > 1 && (
                  <>
                    <button type="button" className="btn btn-outline" onClick={() => setPage(1)}>
                      1
                    </button>
                    {pageNumbers[0] > 2 && <span>…</span>}
                  </>
                )}

                {pageNumbers.map(pageNumber => (
                  <button
                    key={pageNumber}
                    type="button"
                    className={pageNumber === (topics?.page ?? page) ? 'btn' : 'btn btn-outline'}
                    onClick={() => setPage(pageNumber)}
                  >
                    {pageNumber}
                  </button>
                ))}

                {(pageNumbers[pageNumbers.length - 1] ?? 1) < (topics?.total_pages ?? 1) && (
                  <>
                    {(pageNumbers[pageNumbers.length - 1] ?? 1) < (topics?.total_pages ?? 1) - 1 && <span>…</span>}
                    <button
                      type="button"
                      className="btn btn-outline"
                      onClick={() => setPage(topics?.total_pages ?? 1)}
                    >
                      {topics?.total_pages ?? 1}
                    </button>
                  </>
                )}
              </div>

              <button
                type="button"
                className="btn btn-outline"
                disabled={(topics?.page ?? 1) >= (topics?.total_pages ?? 1)}
                onClick={() => setPage(current => Math.min(topics?.total_pages ?? current, current + 1))}
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
