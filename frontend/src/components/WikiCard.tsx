import { Link } from 'react-router-dom'
import { formatDate } from '@/lib/utils'
import HealthBadge from './HealthBadge'
import type { WikiTopic } from '@/api/useWiki'

interface WikiCardProps {
  topic: WikiTopic
}

export default function WikiCard({ topic }: WikiCardProps) {
  return (
    <Link
      to={`/wiki/${topic.topic}`}
      className="block bg-white rounded-xl border border-gray-100 p-4 hover:shadow-md hover:border-brand-500 transition-all"
      data-testid="wiki-card"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-semibold text-gray-900 line-clamp-2">{topic.title || topic.topic}</h3>
        <HealthBadge status="active" label="active" />
      </div>
      <div className="flex flex-wrap gap-1 mb-3">
        {topic.doc_type && topic.doc_type !== 'reference' && (
          <span className="badge badge-gray">{topic.doc_type}</span>
        )}
        {(topic.tags ?? []).map(tag => (
          <span key={tag} className="badge badge-blue">{tag}</span>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>{topic.word_count ?? 0} 字</span>
        <span>{formatDate(topic.updated_at)}</span>
      </div>
    </Link>
  )
}
