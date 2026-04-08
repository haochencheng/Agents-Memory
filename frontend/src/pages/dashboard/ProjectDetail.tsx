import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { type ProjectWikiNavItem, type ProjectWikiNavNode, useProjectStats, useProjectWikiNav } from '@/api/useProjects'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import HealthBadge from '@/components/HealthBadge'
import StatCard from '@/components/StatCard'
import WikiCard from '@/components/WikiCard'

type WikiViewMode = 'tree' | 'domain' | 'list'

function collectInitiallyExpandedNodeKeys(nodes: ProjectWikiNavNode[]) {
  const expanded: string[] = []

  const walk = (items: ProjectWikiNavNode[]) => {
    items.forEach(node => {
      if (node.depth < 2) {
        expanded.push(node.key)
      }
      walk(node.children)
    })
  }

  walk(nodes)
  return expanded
}

function TreeLeaf({
  topic,
  selectedKey,
}: Readonly<{
  topic: ProjectWikiNavItem
  selectedKey: string | null
}>) {
  const isSelected = selectedKey === topic.topic

  return (
    <div
      className={isSelected ? 'rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 shadow-sm' : 'rounded-lg border border-slate-200 bg-white px-3 py-2'}
      data-testid="project-tree-topic"
    >
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

function TreeBranch({
  node,
  expandedKeys,
  onToggleNode,
  selectedKey,
}: Readonly<{
  node: ProjectWikiNavNode
  expandedKeys: string[]
  onToggleNode: (key: string) => void
  selectedKey: string | null
}>) {
  const isOpen = expandedKeys.includes(node.key)
  const isSelected = selectedKey === node.key

  return (
    <div
      className={isSelected ? 'rounded-xl border border-blue-200 bg-blue-50/70 p-3 shadow-sm' : 'rounded-xl border border-slate-200 bg-slate-50/70 p-3'}
      data-testid="project-tree-node"
    >
      <button type="button" className="flex w-full items-center justify-between gap-3 text-left" onClick={() => onToggleNode(node.key)}>
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 w-3 text-xs font-semibold text-slate-500">{isOpen ? 'v' : '>'}</span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{node.label}</p>
            <p className="truncate text-xs text-slate-500 font-mono">{node.path}</p>
          </div>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-600 border border-slate-200">{node.item_count} docs</span>
      </button>

      {isOpen && (
        <div className="mt-3 space-y-3 border-l border-slate-200 pl-4">
          {node.topics.map(topic => (
            <TreeLeaf key={topic.topic} topic={topic} selectedKey={selectedKey} />
          ))}
          {node.children.map(child => (
            <TreeBranch
              key={child.key}
              node={child}
              expandedKeys={expandedKeys}
              onToggleNode={onToggleNode}
              selectedKey={selectedKey}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ExplorerNode({
  node,
  depth,
  expandedKeys,
  selectedKey,
  onToggleNode,
  onSelectTarget,
}: Readonly<{
  node: ProjectWikiNavNode
  depth: number
  expandedKeys: string[]
  selectedKey: string | null
  onToggleNode: (key: string) => void
  onSelectTarget: (key: string) => void
}>) {
  const isOpen = expandedKeys.includes(node.key)
  const isSelected = selectedKey === node.key
  const indent = 10 + depth * 14

  return (
    <div className="space-y-1">
      <button
        type="button"
        className={isSelected ? 'flex w-full items-center gap-2 rounded-lg bg-brand-50 px-2 py-1.5 text-left text-sm font-medium text-brand-700' : 'flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900'}
        style={{ paddingLeft: `${indent}px` }}
        onClick={() => {
          onToggleNode(node.key)
          onSelectTarget(node.key)
        }}
        data-testid="project-explorer-node"
      >
        <span className="w-3 text-[10px] font-semibold text-gray-400">{isOpen ? 'v' : '>'}</span>
        <span className="min-w-0 flex-1 truncate">{node.label}</span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">{node.item_count}</span>
      </button>

      {isOpen && (
        <div className="space-y-1">
          {node.topics.map(topic => {
            return (
              <Link
                key={topic.topic}
                to={`/wiki/${topic.topic}`}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-900"
                style={{ paddingLeft: `${indent + 18}px` }}
                data-testid="project-explorer-topic"
              >
                <span className="w-3 text-[10px] text-gray-400">-</span>
                <span className="truncate">{topic.title}</span>
              </Link>
            )
          })}

          {node.children.map(child => (
            <ExplorerNode
              key={child.key}
              node={child}
              depth={depth + 1}
              expandedKeys={expandedKeys}
              selectedKey={selectedKey}
              onToggleNode={onToggleNode}
              onSelectTarget={onSelectTarget}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ProjectDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const { data: stats, isLoading, error } = useProjectStats(id)
  const { data: wikiNav, isLoading: wikiNavLoading, error: wikiNavError } = useProjectWikiNav(id)
  const [viewMode, setViewMode] = useState<WikiViewMode>('tree')
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)

  const projectWikis = wikiNav?.items ?? []

  useEffect(() => {
    if (!wikiNav) return

    setExpandedKeys(collectInitiallyExpandedNodeKeys(wikiNav.tree))
    setSelectedKey(wikiNav.tree[0]?.key ?? wikiNav.items[0]?.topic ?? null)
  }, [wikiNav])

  const toggleNode = (key: string) => {
    setExpandedKeys(current => (current.includes(key) ? current.filter(item => item !== key) : [...current, key]))
    setSelectedKey(key)
  }

  const selectTreeTarget = (key: string) => {
    setSelectedKey(key)
    if (viewMode !== 'tree') {
      setViewMode('tree')
    }
  }

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

          <div className="grid gap-4 xl:grid-cols-[280px,minmax(0,1fr)]">
            <aside className="self-start xl:sticky xl:top-6" data-testid="project-wiki-sidebar">
              <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
                <div className="border-b border-gray-100 px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Wiki</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">Project Explorer</p>
                  <p className="mt-1 text-xs text-gray-500">目录可展开，文件点击后直接打开 wiki 详情。</p>
                </div>
                <div className="max-h-[70vh] overflow-y-auto px-2 py-3">
                  <div className="space-y-1.5">
                    {wikiNav.tree.map(node => (
                      <ExplorerNode
                        key={node.key}
                        node={node}
                        depth={0}
                        expandedKeys={expandedKeys}
                        selectedKey={selectedKey}
                        onToggleNode={toggleNode}
                        onSelectTarget={selectTreeTarget}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </aside>

            <div className="space-y-4">
              {viewMode === 'tree' && (
                <div className="space-y-3" data-testid="project-wiki-tree-view">
                  {wikiNav.tree.map(node => (
                    <TreeBranch
                      key={node.key}
                      node={node}
                      expandedKeys={expandedKeys}
                      onToggleNode={toggleNode}
                      selectedKey={selectedKey}
                    />
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
            </div>
          </div>

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
