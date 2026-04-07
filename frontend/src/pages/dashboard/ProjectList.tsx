import { Link } from 'react-router-dom'
import { useProjects, useProjectStats } from '@/api/useProjects'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import HealthBadge from '@/components/HealthBadge'

function ProjectCard({ name }: { name: string }) {
  const { data } = useProjectStats(name)
  return (
    <Link
      to={`/projects/${name}`}
      className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow block"
      data-testid="project-card"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800 truncate">{name}</h3>
        <HealthBadge status={data?.health ?? 'unknown'} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs text-gray-500">
        <div>
          <div className="text-lg font-bold text-gray-700">{data?.wiki_count ?? '—'}</div>
          <div>wiki</div>
        </div>
        <div>
          <div className="text-lg font-bold text-gray-700">{data?.error_count ?? '—'}</div>
          <div>errors</div>
        </div>
        <div>
          <div className="text-lg font-bold text-gray-700">{data?.checklist_done ?? '—'}</div>
          <div>checks</div>
        </div>
      </div>
    </Link>
  )
}

export default function ProjectList() {
  const { data: projects, isLoading, error } = useProjects()

  if (isLoading) return <LoadingSpinner text="加载项目列表..." />
  if (error) return <ErrorAlert message="项目列表加载失败" />

  return (
    <div className="space-y-6" data-testid="project-list-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">接入项目</h1>
        <span className="text-sm text-gray-500">{projects?.projects?.length ?? 0} 个项目</span>
      </div>

      {(!projects?.projects || projects.projects.length === 0) ? (
        <div className="bg-white rounded-xl border border-gray-100 p-12 text-center">
          <div className="text-4xl mb-3">📁</div>
          <p className="text-gray-500">暂无接入项目</p>
          <p className="text-sm text-gray-400 mt-1">通过 CLI 或 API 添加项目后在此展示</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.projects.map(p => (
            <ProjectCard key={p.name} name={p.name} />
          ))}
        </div>
      )}
    </div>
  )
}
