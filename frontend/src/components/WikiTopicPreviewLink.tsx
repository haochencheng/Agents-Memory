import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useWikiTopicWithOptions } from '@/api/useWiki'
import { extractWikiPreview } from '@/lib/wikiPreview'

interface WikiTopicPreviewLinkProps {
  topic: string
  title: string
}

export default function WikiTopicPreviewLink({ topic, title }: WikiTopicPreviewLinkProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { data } = useWikiTopicWithOptions(topic, { enabled: isOpen })
  const summary = extractWikiPreview(data?.raw ?? '')

  return (
    <div
      className="relative group/page"
      onMouseEnter={() => setIsOpen(true)}
      onFocus={() => setIsOpen(true)}
    >
      <Link
        to={`/wiki/${encodeURIComponent(topic)}`}
        className="pointer-events-auto block rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600 hover:border-blue-200 hover:text-blue-700"
      >
        <div className="font-medium text-slate-900">{title}</div>
        <div className="mt-1 truncate">{topic}</div>
      </Link>

      <div className="pointer-events-none invisible absolute left-0 top-full z-30 mt-2 w-72 rounded-xl border border-slate-200 bg-white p-4 text-left shadow-xl transition duration-150 group-hover/page:visible group-hover/page:pointer-events-auto group-focus-within/page:visible group-focus-within/page:pointer-events-auto">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">{data?.title || title}</div>
            <div className="mt-1 text-xs text-slate-500">
              {data?.doc_type || 'wiki'} {data?.project ? `· ${data.project}` : ''}
            </div>
          </div>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
            {data?.word_count ?? 0} 字
          </span>
        </div>

        <div className="mt-3 text-xs leading-5 text-slate-600">
          {summary || '正在加载摘要，或该页面暂时没有可用正文。'}
        </div>

        {data?.related_topics?.length ? (
          <div className="mt-3">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">继续阅读</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {data.related_topics.slice(0, 2).map(item => (
                <span key={`${topic}-${item.topic}`} className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
                  {item.title || item.topic}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
