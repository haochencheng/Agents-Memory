import { useParams, Link } from 'react-router-dom'
import { useProjectStats } from '@/api/useProjects'
import { useWikiList } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import HealthBadge from '@/components/HealthBadge'
import StatCard from '@/components/StatCard'
import WikiCard from '@/components/WikiCard'

export default function ProjectDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const { data: stats, isLoading, error } = useProjectStats(id)
  const { data: wikis } = useWikiList()

  const projectWikis = (wikis?.topics ?? []).filter(w => w.project === id)

  if (isLoading) return <LoadingSpinner text={`加载项目 ${id}...`} />
  if (error) return <ErrorAlert message={`项目 "${id}" 信息加载失败`} />

  return (
    <div className="space-y-6" data-testid="project-detail-page">
      <div className="flex items-center gap-3">
        <Link to="/projects" className="text-sm text-blue-500 hover:underline">← 返回项目列表</Link>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="page-title font-mono">{id}</h1>
        <HealthBadge status={stats?.health ?? 'unknown'} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Wiki 页面" value={stats?.wiki_count ?? 0} icon="📚" />
        <StatCard label="错误记录" value={stats?.error_count ?? 0} icon="🐛" />
        <StatCard label="Check 完成" value={stats?.checklist_done ?? 0} icon="✅" />
        <StatCard label="摄入次数" value={stats?.ingest_count ?? 0} icon="📥" />
      </div>

      {projectWikis.length > 0 && (
        <div>
          <h2 className="section-title mb-3">Wiki 页面</h2>
          <div className="space-y-3">
            {projectWikis.map(w => (
              <WikiCard key={w.topic} topic={w} />
            ))}
          </div>
        </div>
      )}

      {stats?.last_ingest && (
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <h2 className="section-title mb-2">最近摄入</h2>
          <p className="text-sm font-mono text-gray-700 bg-gray-50 rounded p-3">{stats.last_ingest}</p>
        </div>
      )}

      {stats?.last_error && (
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <h2 className="section-title mb-2">最近错误</h2>
          <p className="text-sm font-mono text-gray-700 bg-gray-50 rounded p-3">{stats.last_error}</p>
        </div>
      )}
    </div>
  )
}
