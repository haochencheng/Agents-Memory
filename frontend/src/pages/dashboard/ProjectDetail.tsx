import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { type ProjectWikiNavItem, type ProjectWikiNavNode, useProjectStats, useProjectWikiNav } from '@/api/useProjects'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import HealthBadge from '@/components/HealthBadge'
import StatCard from '@/components/StatCard'
import WikiCard from '@/components/WikiCard'

type WikiViewMode = 'tree' | 'domain' | 'list'

function TreeLeaf({ topic }: Readonly<{ topic: ProjectWikiNavItem }>) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2" data-testid="project-tree-topic">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link to={`/wiki/${topic.topic}`} className="text-sm font-semibold text-slate-900 hover:text-blue-600 hover:underline">
            {topic.title}
          </Link>
          <p className="mt-1 text-xs text-slate-500 font-mono">{topic.source_path || topic.topic}</p>
        </div>
        <span className="text-xs text-slate-400 whitespace-nowrap">{topic.word_count} 字</span>
      </div>
    </div>
  )
}

function TreeBranch({ node }: Readonly<{ node: ProjectWikiNavNode }>) {
  const shouldStartOpen = node.depth < 2
  return (
    <details className="rounded-xl border border-slate-200 bg-slate-50/70 p-3" open={shouldStartOpen} data-testid="project-tree-node">
      <summary className="cursor-pointer list-none">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">{node.label}</p>
            <p className="text-xs text-slate-500 font-mono">{node.path}</p>
          </div>
          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-600 border border-slate-200">{node.item_count} docs</span>
        </div>
      </summary>
      <div className="mt-3 space-y-3 border-l border-slate-200 pl-4">
        {node.topics.map(topic => (
          <TreeLeaf key={topic.topic} topic={topic} />
        ))}
        {node.children.map(child => (
          <TreeBranch key={child.key} node={child} />
        ))}
      </div>
    </details>
  )
}

export default function ProjectDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const { data: stats, isLoading, error } = useProjectStats(id)
  const { data: wikiNav, isLoading: wikiNavLoading, error: wikiNavError } = useProjectWikiNav(id)
  const [viewMode, setViewMode] = useState<WikiViewMode>('tree')

  const projectWikis = wikiNav?.items ?? []

  if (isLoading || wikiNavLoading) return <LoadingSpinner text={`加载项目 ${id}...`} />
  if (error) return <ErrorAlert message={`项目 "${id}" 信息加载失败`} />
  if (wikiNavError) return <ErrorAlert message={`项目 "${id}" 的 wiki 导航加载失败`} />

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

      {projectWikis.length > 0 && wikiNav && (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="section-title">Project Knowledge Explorer</h2>
              <p className="mt-1 text-sm text-slate-500">为大文档项目提供 `Tree / Domain / List` 三种浏览方式；`source_path` 仍是稳定真源。</p>
            </div>
            <div className="flex flex-wrap gap-2" data-testid="project-wiki-view-tabs">
              {([
                ['tree', 'Tree'],
                ['domain', 'Domain'],
                ['list', 'List'],
              ] as const).map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  className={viewMode === mode ? 'rounded-full bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white' : 'rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600'}
                  onClick={() => setViewMode(mode)}
                >
                  {label}
                </button>
              ))}
              <Link to="/wiki/graph" className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-blue-600">
                Graph
              </Link>
            </div>
          </div>

          {viewMode === 'tree' && (
            <div className="space-y-3" data-testid="project-wiki-tree-view">
              {wikiNav.tree.map(node => (
                <TreeBranch key={node.key} node={node} />
              ))}
            </div>
          )}

          {viewMode === 'domain' && (
            <div className="space-y-4" data-testid="project-wiki-domain-view">
              {wikiNav.groups.map(group => (
                <section key={group.key} className="rounded-xl border border-slate-200 bg-white p-4" data-testid="project-domain-group">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">{group.label}</h3>
                      <p className="text-xs text-slate-500">规则分组视图，便于按知识域浏览。</p>
                    </div>
                    <span className="rounded-full bg-slate-50 px-2.5 py-1 text-xs text-slate-600 border border-slate-200">{group.item_count} docs</span>
                  </div>
                  <div className="space-y-3">
                    {group.topics.map(topic => (
                      <WikiCard key={topic.topic} topic={topic} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}

          {viewMode === 'list' && (
            <div className="space-y-3" data-testid="project-wiki-list-view">
              {projectWikis.map(w => (
                <WikiCard key={w.topic} topic={w} />
              ))}
            </div>
          )}

          <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-sm text-slate-600">
            <p className="font-medium text-slate-900">当前共 {wikiNav.total_topics} 篇项目 wiki。</p>
            <p className="mt-1">`Tree` 基于物理路径生成，`Domain` 基于规则分组生成；后续如引入 LLM/agent，只用于优化分组命名与摘要，不替代真实来源路径。</p>
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
