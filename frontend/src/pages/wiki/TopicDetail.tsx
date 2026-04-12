import { useParams, Link } from 'react-router-dom'
import { useWikiTopic } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'
import type { TopicRelation } from '@/api/useWiki'

// Simple markdown-to-HTML renderer (no external dep)
function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold mt-5 mb-2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-6 mb-3">$1</h1>')
    .replace(/\[\[([^\]]+)\]\]/g, '<a class="text-blue-600 underline" href="/wiki/$1">$1</a>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a class="text-blue-600 underline" href="$2">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 rounded text-sm font-mono">$1</code>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\n\n/g, '</p><p class="mb-3">')
    .replace(/^(?!<[h|l])(.+)$/gm, '<p class="mb-3">$1</p>')
}

function RelationSection({ title, items }: { title: string; items: TopicRelation[] }) {
  if (items.length === 0) return null

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-100 p-5">
      <h2 className="section-title mb-3">{title}</h2>
      <div className="space-y-3">
        {items.map(item => (
          <div key={`${title}-${item.topic}`} className="rounded-lg border border-gray-200 bg-white px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <Link to={`/wiki/${encodeURIComponent(item.topic)}`} className="font-medium text-slate-900 hover:text-blue-600 hover:underline">
                {item.title || item.topic}
              </Link>
              <span className="badge badge-blue">{item.relation}</span>
            </div>
            {item.reason && <p className="mt-2 text-sm text-gray-500">{item.reason}</p>}
          </div>
        ))}
      </div>
    </div>
  )
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
        <h1 className="page-title">{data?.title || topic}</h1>
        {data?.updated_at && (
          <span className="text-xs text-gray-400">
            更新于 {formatDate(data.updated_at)}
          </span>
        )}
      </div>

      {(data?.project || data?.source_path || data?.doc_type) && (
        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
          {data?.project && <span className="rounded-full bg-slate-100 px-3 py-1.5">项目: {data.project}</span>}
          {data?.doc_type && <span className="rounded-full bg-slate-100 px-3 py-1.5">类型: {data.doc_type}</span>}
          {data?.source_path && <span className="rounded-full bg-slate-100 px-3 py-1.5">来源: {data.source_path}</span>}
        </div>
      )}

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

      <RelationSection title="显式链接" items={data?.links ?? []} />
      <RelationSection title="反向引用" items={data?.backlinks ?? []} />
      <RelationSection title="自动推荐关联页面" items={data?.related_topics ?? []} />
    </div>
  )
}
