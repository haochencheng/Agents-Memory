import { useParams, Link } from 'react-router-dom'
import { useWikiTopic } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

// Simple markdown-to-HTML renderer (no external dep)
function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold mt-5 mb-2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-6 mb-3">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 rounded text-sm font-mono">$1</code>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\n\n/g, '</p><p class="mb-3">')
    .replace(/^(?!<[h|l])(.+)$/gm, '<p class="mb-3">$1</p>')
}

export default function TopicDetail() {
  const { topic = '' } = useParams<{ topic: string }>()
  const { data, isLoading, error } = useWikiTopic(topic)

  if (isLoading) return <LoadingSpinner text={`加载 ${topic}...`} />
  if (error) return <ErrorAlert message={`Wiki 页面 "${topic}" 加载失败`} />

  const content: string = data?.raw ?? data?.content_html ?? ''

  return (
    <div className="space-y-6" data-testid="topic-detail-page">
      <div className="flex items-center gap-3">
        <Link to="/wiki" className="text-sm text-blue-500 hover:underline">← 返回 Wiki</Link>
        <Link
          to={`/wiki/${encodeURIComponent(topic)}/edit`}
          className="ml-auto text-sm text-blue-500 border border-blue-300 rounded px-3 py-1 hover:bg-blue-50"
        >
          ✏️ 编辑
        </Link>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="page-title">{topic}</h1>
        {data?.updated_at && (
          <span className="text-xs text-gray-400">
            更新于 {formatDate(data.updated_at)}
          </span>
        )}
      </div>

      {/* Tags */}
      {Array.isArray(data?.tags) && data.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {data.tags.map((tag: string) => (
            <span key={tag} className="badge badge-blue">{tag}</span>
          ))}
        </div>
      )}

      {/* Content */}
      <div
        className="bg-white rounded-xl border border-gray-100 p-6 prose prose-sm max-w-none"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
      />

      {/* Backlinks */}
      {Array.isArray(data?.frontmatter?.backlinks) && (data.frontmatter.backlinks as string[]).length > 0 && (
        <div className="bg-gray-50 rounded-xl border border-gray-100 p-5">
          <h2 className="section-title mb-3">链接此页面</h2>
          <div className="flex flex-wrap gap-2">
            {(data.frontmatter.backlinks as string[]).map((l: string) => (
              <Link
                key={l}
                to={`/wiki/${encodeURIComponent(l)}`}
                className="text-sm text-blue-500 hover:underline"
              >
                {l}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
