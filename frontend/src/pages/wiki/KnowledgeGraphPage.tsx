import { type FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useWikiGraph } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import {
  type GraphExplorerView,
  type GraphRelationFilter,
  buildExploreModel,
  buildFilterOptions,
  buildSchemaSummary,
  buildTableRows,
  edgeColor,
  formatNodeType,
  formatProject,
  graphCanvasSize,
} from '@/lib/knowledgeGraph'

const VIEW_LABELS: Record<GraphExplorerView, string> = {
  schema: 'Schema',
  explore: 'Explore',
  table: 'Table',
}
const RELATION_LABELS: Record<GraphRelationFilter, string> = {
  all: '全部关系',
  explicit: '显式关系',
  inferred: '推断关系',
}

function viewFromParams(searchParams: URLSearchParams): GraphExplorerView {
  const requested = searchParams.get('view')
  const node = searchParams.get('node')
  if (requested === 'schema' || requested === 'explore' || requested === 'table') {
    return requested
  }
  return node ? 'explore' : 'schema'
}

function relationBadge(relationType?: string) {
  return relationType === 'explicit' ? 'badge badge-blue' : 'badge badge-gray'
}

export default function KnowledgeGraphPage() {
  const { data, isLoading, error } = useWikiGraph()
  const [searchParams, setSearchParams] = useSearchParams()
  const [view, setView] = useState<GraphExplorerView>(() => viewFromParams(searchParams))
  const [projectFilter, setProjectFilter] = useState('all')
  const [nodeTypeFilter, setNodeTypeFilter] = useState('all')
  const [relationFilter, setRelationFilter] = useState<GraphRelationFilter>('all')
  const [draftQuery, setDraftQuery] = useState('')
  const [query, setQuery] = useState('')
  const [depth, setDepth] = useState<1 | 2>(1)
  const requestedNodeId = searchParams.get('node') ?? ''
  const [selectedId, setSelectedId] = useState(requestedNodeId)

  const nodes = data?.nodes ?? []
  const edges = data?.edges ?? []
  const filterOptions = useMemo(() => buildFilterOptions(nodes), [nodes])
  const filters = useMemo(
    () => ({
      project: projectFilter,
      nodeType: nodeTypeFilter,
      relation: relationFilter,
      query,
    }),
    [nodeTypeFilter, projectFilter, query, relationFilter],
  )
  const schema = useMemo(() => buildSchemaSummary(nodes, edges), [edges, nodes])
  const explore = useMemo(
    () => buildExploreModel(nodes, edges, filters, selectedId || requestedNodeId, depth),
    [depth, edges, filters, nodes, requestedNodeId, selectedId],
  )
  const tableRows = useMemo(() => buildTableRows(nodes, edges, filters), [edges, filters, nodes])
  const { width: canvasWidth, height: canvasHeight } = graphCanvasSize()

  useEffect(() => {
    const nextView = viewFromParams(searchParams)
    if (nextView !== view) {
      setView(nextView)
    }
  }, [searchParams, view])

  useEffect(() => {
    if (!requestedNodeId) return
    if (requestedNodeId !== selectedId) {
      setSelectedId(requestedNodeId)
    }
  }, [requestedNodeId, selectedId])

  const writeParams = (next: { nodeId?: string; nextView?: GraphExplorerView }) => {
    const updated = new URLSearchParams(searchParams)
    const resolvedView = next.nextView ?? view
    updated.set('view', resolvedView)
    if (next.nodeId) {
      updated.set('node', next.nodeId)
    } else if (!requestedNodeId && !next.nodeId) {
      updated.delete('node')
    }
    setSearchParams(updated, { replace: true })
  }

  const switchView = (nextView: GraphExplorerView) => {
    setView(nextView)
    writeParams({ nextView, nodeId: explore.focusNode?.id || selectedId || undefined })
  }

  const selectNode = (nodeId: string, nextView: GraphExplorerView = 'explore') => {
    setSelectedId(nodeId)
    setView(nextView)
    writeParams({ nodeId, nextView })
  }

  const explicitCount = edges.filter(edge => edge.type === 'explicit').length
  const inferredCount = edges.filter(edge => edge.type === 'inferred').length

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setQuery(draftQuery.trim())
  }

  return (
    <div className="space-y-5" data-testid="knowledge-graph-page">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="page-title">知识图谱</h1>
          <p className="mt-1 text-sm text-gray-500">
            默认先看 schema，再进入局部 explore，最后用 table 做精确筛选，避免把全量节点一次性压进一张不可读的画布。
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
          <span className="rounded-full bg-slate-100 px-3 py-1.5">{nodes.length} 概念节点</span>
          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-blue-700">{explicitCount} 显式关系</span>
          <span className="rounded-full bg-slate-100 px-3 py-1.5">{inferredCount} 推断关系</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.entries(VIEW_LABELS) as Array<[GraphExplorerView, string]>).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={view === value ? 'btn' : 'btn btn-outline'}
            onClick={() => switchView(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-3 rounded-xl border border-gray-100 bg-white p-4 md:grid-cols-2 xl:grid-cols-5">
        <form className="space-y-1 md:col-span-2 xl:col-span-2" onSubmit={handleSearchSubmit}>
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">搜索</span>
          <div className="flex max-w-3xl items-stretch gap-3">
            <input
              value={draftQuery}
              onChange={event => setDraftQuery(event.target.value)}
              className="input h-12 min-w-0 flex-1"
              placeholder="概念、项目、标签..."
              data-testid="knowledge-graph-search-input"
            />
            <button type="submit" className="btn h-12 px-5" data-testid="knowledge-graph-search-submit">
              搜索
            </button>
          </div>
        </form>

        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">项目</span>
          <select value={projectFilter} onChange={event => setProjectFilter(event.target.value)} className="input w-full">
            <option value="all">全部项目</option>
            {filterOptions.projects.map(project => (
              <option key={project} value={project}>
                {formatProject(project)}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">类型</span>
          <select value={nodeTypeFilter} onChange={event => setNodeTypeFilter(event.target.value)} className="input w-full">
            <option value="all">全部类型</option>
            {filterOptions.nodeTypes.map(nodeType => (
              <option key={nodeType} value={nodeType}>
                {formatNodeType(nodeType)}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">关系</span>
          <select
            value={relationFilter}
            onChange={event => setRelationFilter(event.target.value as GraphRelationFilter)}
            className="input w-full"
          >
            {(Object.entries(RELATION_LABELS) as Array<[GraphRelationFilter, string]>).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Explore 深度</span>
          <select value={depth} onChange={event => setDepth(Number(event.target.value) as 1 | 2)} className="input w-full">
            <option value={1}>1-hop 邻居</option>
            <option value={2}>2-hop 邻居</option>
          </select>
        </label>
      </div>

      {isLoading && <LoadingSpinner text="加载知识图谱..." />}
      {error && <ErrorAlert message="知识图谱加载失败" />}

      {!isLoading && !error && nodes.length === 0 && (
        <div className="rounded-xl border bg-white p-10 text-center text-gray-500">
          <div className="text-4xl">🕸️</div>
          <p className="mt-3">当前没有可展示的关系。</p>
        </div>
      )}

      {!isLoading && !error && nodes.length > 0 && view === 'schema' && (
        <div className="space-y-4" data-testid="graph-schema-view">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {schema.nodeTypes.map(summary => (
              <div key={summary.key} className="rounded-xl border border-gray-100 bg-white p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{summary.label}</div>
                <div className="mt-3 text-3xl font-bold text-slate-900">{summary.count}</div>
                <div className="mt-2 text-sm text-slate-500">{summary.connectedCount} 个已连接概念</div>
              </div>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="rounded-xl border border-gray-100 bg-white p-4">
              <h2 className="text-base font-semibold text-slate-900">Project Schema Explorer</h2>
              <p className="mt-1 text-sm text-slate-500">先按项目和类型看覆盖面，再决定要不要进入局部关系图。</p>

              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm" data-testid="graph-schema-table">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                      <th className="px-3 py-2">项目</th>
                      <th className="px-3 py-2">总节点</th>
                      <th className="px-3 py-2">已连接</th>
                      {schema.nodeTypes.map(nodeType => (
                        <th key={nodeType.key} className="px-3 py-2">{nodeType.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {schema.projects.map(project => (
                      <tr key={project.project} className="border-b border-slate-100 last:border-b-0">
                        <td className="px-3 py-3 font-medium text-slate-900">{formatProject(project.project)}</td>
                        <td className="px-3 py-3 text-slate-600">{project.total}</td>
                        <td className="px-3 py-3 text-slate-600">{project.connected}</td>
                        {schema.nodeTypes.map(nodeType => (
                          <td key={`${project.project}-${nodeType.key}`} className="px-3 py-3 text-slate-600">
                            {project.breakdown[nodeType.key] ?? 0}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <h2 className="text-base font-semibold text-slate-900">关系概览</h2>
                <div className="mt-4 space-y-3">
                  {schema.relationTypes.map(relation => (
                    <div key={relation.key} className="rounded-lg bg-slate-50 px-3 py-3">
                      <div className="text-xs uppercase tracking-wide text-slate-400">{relation.label}</div>
                      <div className="mt-1 text-2xl font-bold text-slate-900">{relation.count}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <h2 className="text-base font-semibold text-slate-900">浏览建议</h2>
                <ul className="mt-3 space-y-2 text-sm text-slate-500">
                  <li>Schema 先回答“这个知识库里有哪些类型和项目”。</li>
                  <li>Explore 只展示一个焦点节点的局部 1-hop / 2-hop 网络。</li>
                  <li>Table 适合按项目、类型、搜索词精确筛选并跳转阅读。</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {!isLoading && !error && nodes.length > 0 && view === 'explore' && (
        <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_320px]" data-testid="graph-explore-view">
          <div className="rounded-xl border border-gray-100 bg-white p-4">
            <h2 className="text-base font-semibold text-slate-900">Explore Candidates</h2>
            <p className="mt-1 text-sm text-slate-500">从筛选结果里选一个焦点节点，只展开局部邻居。</p>
            <div className="mt-4 space-y-2" data-testid="graph-candidate-list">
              {explore.candidateNodes.length === 0 && (
                <div className="rounded-lg border border-dashed border-slate-200 px-3 py-4 text-sm text-slate-400">
                  当前筛选条件下没有可探索的概念。
                </div>
              )}
              {explore.candidateNodes.map(node => (
                <button
                  key={node.id}
                  type="button"
                  className={`w-full rounded-lg border px-3 py-3 text-left transition ${
                    explore.focusNode?.id === node.id
                      ? 'border-blue-200 bg-blue-50'
                      : 'border-slate-200 hover:border-blue-200 hover:bg-slate-50'
                  }`}
                  onClick={() => selectNode(node.id)}
                >
                  <div className="text-sm font-medium text-slate-900">{node.title || node.id}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {formatNodeType(node.node_type)} · {formatProject(node.project)} · {node.degree} edges
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-gray-100 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Local Graph Explorer</h2>
                <p className="mt-1 text-sm text-slate-500">当前只渲染焦点节点的局部邻居，避免全量图变成文字毛球。</p>
              </div>
              <div className="text-xs text-slate-400">
                {explore.visibleNodes.length} nodes / {explore.visibleEdges.length} edges
              </div>
            </div>

            {explore.focusNode ? (
              <div className="mt-4 overflow-auto">
                <svg
                  width={canvasWidth}
                  height={canvasHeight}
                  viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
                  className="min-w-[720px]"
                  data-testid="graph-canvas"
                >
                  {explore.visibleEdges.map(edge => {
                    const source = explore.visibleNodes.find(node => node.id === edge.source)
                    const target = explore.visibleNodes.find(node => node.id === edge.target)
                    if (!source || !target) return null
                    return (
                      <line
                        key={`${edge.source}-${edge.target}-${edge.type}`}
                        x1={source.x}
                        y1={source.y}
                        x2={target.x}
                        y2={target.y}
                        stroke={edgeColor(edge)}
                        strokeOpacity={edge.type === 'explicit' ? 0.8 : 0.35}
                        strokeWidth={edge.type === 'explicit' ? 2 : 1.2}
                      />
                    )
                  })}

                  {explore.visibleNodes.map(node => (
                    <g key={node.id} onClick={() => selectNode(node.id)} style={{ cursor: 'pointer' }}>
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={node.id === explore.focusNode?.id ? 12 : Math.max(7, Math.min(10, 7 + node.degree * 0.25))}
                        fill={node.id === explore.focusNode?.id ? '#0f172a' : '#2563eb'}
                        stroke={node.distance === 1 ? '#93c5fd' : '#e2e8f0'}
                        strokeWidth={node.id === explore.focusNode?.id ? 4 : 2}
                      />
                      <text x={node.x} y={node.y + 28} textAnchor="middle" fill="#0f172a" fontSize="11" fontWeight="600">
                        {(node.title || node.id).length > 20 ? `${(node.title || node.id).slice(0, 18)}…` : (node.title || node.id)}
                      </text>
                    </g>
                  ))}
                </svg>
              </div>
            ) : (
              <div className="mt-4 rounded-lg border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-400">
                当前筛选条件下没有可探索的概念。
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-gray-100 bg-white p-4">
              <h2 className="text-base font-semibold text-slate-900">阅读提示</h2>
              <div className="mt-3 space-y-2 text-sm text-slate-500">
                <p>Explore 不是全量总览，而是围绕一个概念展开局部关系。</p>
                <p>优先确认显式边，推断边只做线索，不直接当真理。</p>
              </div>
            </div>

            {explore.focusNode && (
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">{explore.focusNode.title || explore.focusNode.id}</h2>
                    <p className="mt-1 text-xs text-slate-500">
                      {formatNodeType(explore.focusNode.node_type)} · {formatProject(explore.focusNode.project)}
                    </p>
                  </div>
                  {explore.focusNode.primary_topic ? (
                    <Link
                      to={`/wiki/${encodeURIComponent(explore.focusNode.primary_topic)}`}
                      className="text-sm font-medium text-blue-600 hover:underline"
                    >
                      打开页面
                    </Link>
                  ) : (
                    <span className="text-sm text-slate-400">无直接页面</span>
                  )}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-lg bg-slate-50 px-3 py-2">
                    <div className="text-xs text-slate-400">连接数</div>
                    <div className="mt-1 font-semibold text-slate-900">{explore.focusNode.degree}</div>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-3 py-2">
                    <div className="text-xs text-slate-400">关联页面数</div>
                    <div className="mt-1 font-semibold text-slate-900">{explore.focusNode.topic_count ?? 0}</div>
                  </div>
                </div>

                <div className="mt-4">
                  <h3 className="text-sm font-semibold text-slate-900">邻居节点</h3>
                  <div className="mt-3 space-y-3">
                    {explore.neighbors.length === 0 && (
                      <p className="text-sm text-slate-400">这个概念当前还没有稳定邻居。</p>
                    )}
                    {explore.neighbors.map(({ edge, node }) => (
                      <div key={`${explore.focusNode?.id}-${node.id}`} className="rounded-lg border border-slate-200 px-3 py-3">
                        <div className="flex items-center justify-between gap-2">
                          {node.primary_topic ? (
                            <Link
                              to={`/wiki/${encodeURIComponent(node.primary_topic)}`}
                              className="font-medium text-slate-900 hover:text-blue-600 hover:underline"
                            >
                              {node.title || node.id}
                            </Link>
                          ) : (
                            <button
                              type="button"
                              className="font-medium text-slate-900 hover:text-blue-600"
                              onClick={() => selectNode(node.id)}
                            >
                              {node.title || node.id}
                            </button>
                          )}
                          <span className={relationBadge(edge.type)}>{edge.type === 'explicit' ? '显式' : '推断'}</span>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">
                          {formatNodeType(node.node_type)} · {formatProject(node.project)} · {node.degree} edges
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!isLoading && !error && nodes.length > 0 && view === 'table' && (
        <div className="rounded-xl border border-gray-100 bg-white p-4" data-testid="graph-table-view">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Graph Table Explorer</h2>
              <p className="mt-1 text-sm text-slate-500">用结构化表格精确筛选概念，再跳去 Explore 或原始 wiki 页面。</p>
            </div>
            <div className="text-xs text-slate-400">{tableRows.length} 条结果</div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="graph-table">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-3 py-2">标题</th>
                  <th className="px-3 py-2">类型</th>
                  <th className="px-3 py-2">项目</th>
                  <th className="px-3 py-2">连接数</th>
                  <th className="px-3 py-2">页面数</th>
                  <th className="px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map(row => (
                  <tr key={row.id} className="border-b border-slate-100 last:border-b-0">
                    <td className="px-3 py-3 font-medium text-slate-900">{row.title || row.id}</td>
                    <td className="px-3 py-3 text-slate-600">{formatNodeType(row.node_type)}</td>
                    <td className="px-3 py-3 text-slate-600">{formatProject(row.project)}</td>
                    <td className="px-3 py-3 text-slate-600">{row.degree}</td>
                    <td className="px-3 py-3 text-slate-600">{row.topic_count ?? 0}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="btn btn-outline" onClick={() => selectNode(row.id, 'explore')}>
                          Explore
                        </button>
                        {row.hasPrimaryTopic && row.primary_topic ? (
                          <Link to={`/wiki/${encodeURIComponent(row.primary_topic)}`} className="btn btn-outline">
                            Wiki
                          </Link>
                        ) : (
                          <span className="text-xs text-slate-400">无页面</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
