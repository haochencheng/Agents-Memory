import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { type WorkflowRecord, useWorkflowRecords } from '@/api/useWorkflow'
import { formatDate } from '@/lib/utils'
import { Link } from 'react-router-dom'

export default function Workflow() {
  const { data, isLoading, error } = useWorkflowRecords({ limit: 100 })

  const grouped = (data?.records ?? []).reduce<Record<string, WorkflowRecord[]>>((acc, record) => {
    const key = record.project || 'unknown'
    if (!acc[key]) {
      acc[key] = []
    }
    acc[key].push(record)
    return acc
  }, {})

  const projects = Object.entries(grouped).sort((a, b) => b[1].length - a[1].length)

  return (
    <div className="space-y-6" data-testid="workflow-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Workflow 状态</h1>
        <span className="text-sm text-gray-500">{data?.total ?? 0} 条记录</span>
      </div>

      {isLoading && <LoadingSpinner text="加载工作流记录..." />}
      {error && <ErrorAlert message="工作流数据加载失败" />}

      {!isLoading && !error && projects.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-12 text-center">
          <div className="text-4xl mb-3">🔄</div>
          <p className="text-gray-500">暂无工作流记录</p>
        </div>
      )}

      {!isLoading && !error && projects.length > 0 && (
        <div className="space-y-4">
          {projects.map(([project, records]) => (
            <div key={project} className="bg-white rounded-xl border border-gray-100 p-5">
              <div className="flex items-center justify-between gap-3 mb-4">
                <h3 className="font-semibold text-gray-700 font-mono">{project}</h3>
                <span className="badge badge-blue">{records.length} records</span>
              </div>
              <div className="space-y-3">
                {records.slice(0, 6).map(record => (
                  <Link
                    key={`${project}-${record.id}`}
                    to={`/workflow/${encodeURIComponent(record.id)}`}
                    className="block rounded-lg border border-gray-100 bg-gray-50 p-3 transition hover:border-blue-200 hover:bg-white"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{record.title || record.id}</p>
                        <div className="flex flex-wrap gap-2 mt-1">
                          <span className="badge badge-blue">{record.source_type}</span>
                          <span className="badge badge-gray">{record.status || 'recorded'}</span>
                          <span className="badge badge-gray">{record.storage_kind}</span>
                        </div>
                      </div>
                      <span className="text-xs text-gray-400 flex-shrink-0">{formatDate(record.created_at)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-blue-50 rounded-xl border border-blue-100 p-5">
        <h2 className="section-title text-blue-800">工作流说明</h2>
        <ol className="list-decimal list-inside space-y-1 text-sm text-blue-700 mt-2">
          <li><strong>项目文档</strong>：通过 onboarding 导入到 wiki，作为长期知识。</li>
          <li><strong>失败任务</strong>：写入错误记录，继续参与错误统计与 wiki compile。</li>
          <li><strong>完成任务/需求</strong>：写入 workflow records，保留执行证据但不污染错误面板。</li>
        </ol>
      </div>
    </div>
  )
}
