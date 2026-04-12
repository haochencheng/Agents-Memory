import { Link, useParams } from 'react-router-dom'
import { useErrorDetail } from '@/api/useMemory'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

export default function ErrorDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, error } = useErrorDetail(id)

  if (isLoading) return <LoadingSpinner text={`加载错误记录 ${id}...`} />
  if (error) return <ErrorAlert message={`错误记录 "${id}" 加载失败`} />

  return (
    <div className="space-y-6" data-testid="error-detail-page">
      <div className="flex items-center gap-3">
        <Link to="/memory" className="text-sm text-blue-500 hover:underline">← 返回记忆记录</Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{data?.title || id}</h1>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            {data?.project && <span className="rounded-full bg-slate-100 px-3 py-1.5">项目: {data.project}</span>}
            {data?.status && <span className="rounded-full bg-slate-100 px-3 py-1.5">状态: {data.status}</span>}
          </div>
        </div>
        {data?.created_at && (
          <span className="text-xs text-gray-400">创建于 {formatDate(data.created_at)}</span>
        )}
      </div>

      <div
        className="bg-white rounded-xl border border-gray-100 p-6 prose prose-sm max-w-none"
        dangerouslySetInnerHTML={{ __html: data?.content_html || '' }}
      />
    </div>
  )
}
