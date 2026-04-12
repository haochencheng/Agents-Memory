import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useWikiGraph } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

type GraphFilter = 'all' | 'connected' | 'explicit' | 'inferred'

interface GraphNode {
  id: string
  title?: string
  node_type?: string
  project?: string
  word_count?: number
  tags?: string[]
  primary_topic?: string
  topic_count?: number
}

interface GraphEdge {
  source: string
  target: string
  type?: string
  weight?: number
}

interface PositionedNode extends GraphNode {
  x: number
  y: number
  degree: number
}

const SVG_WIDTH = 1120

function edgeMatchesFilter(edge: GraphEdge, filter: GraphFilter): boolean {
  if (filter === 'explicit') return edge.type === 'explicit'
  if (filter === 'inferred') return edge.type === 'inferred'
  return true
}

function buildGraphState(nodes: GraphNode[], edges: GraphEdge[], filter: GraphFilter) {
  const baseEdges = edges.filter(edge => edgeMatchesFilter(edge, filter))
  const connectedIds = new Set<string>()
  baseEdges.forEach(edge => {
    connectedIds.add(edge.source)
    connectedIds.add(edge.target)
  })

  const visibleNodes = nodes.filter(node => filter !== 'connected' || connectedIds.has(node.id))
  const visibleIds = new Set(visibleNodes.map(node => node.id))
  const visibleEdges = baseEdges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target))
  const degreeMap = new Map<string, number>()

  visibleNodes.forEach(node => degreeMap.set(node.id, 0))
  visibleEdges.forEach(edge => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  })

  const projectOrder = Array.from(
    new Set(visibleNodes.map(node => (node.project?.trim() ? node.project : 'unassigned'))),
  ).sort((left, right) => left.localeCompare(right))

  const laneWidth = Math.max(220, Math.floor((SVG_WIDTH - 120) / Math.max(projectOrder.length, 1)))
  const positionedNodes: PositionedNode[] = []
  let maxRows = 0

  projectOrder.forEach((project, projectIndex) => {
    const groupNodes = visibleNodes
      .filter(node => (node.project?.trim() ? node.project : 'unassigned') === project)
      .sort((left, right) => {
        const degreeDelta = (degreeMap.get(right.id) ?? 0) - (degreeMap.get(left.id) ?? 0)
        if (degreeDelta !== 0) return degreeDelta
        return (left.title || left.id).localeCompare(right.title || right.id)
      })

    maxRows = Math.max(maxRows, groupNodes.length)
    groupNodes.forEach((node, rowIndex) => {
      positionedNodes.push({
        ...node,
        degree: degreeMap.get(node.id) ?? 0,
        x: 70 + projectIndex * laneWidth + laneWidth / 2,
        y: 90 + rowIndex * 42,
      })
    })
  })

  return {
    connectedIds,
    projectOrder,
    laneWidth,
    visibleNodes: positionedNodes,
    visibleEdges,
    height: Math.max(620, 150 + maxRows * 42),
  }
}

function edgeColor(edge: GraphEdge): string {
  return edge.type === 'explicit' ? '#2563eb' : '#94a3b8'
}

function edgeOpacity(edge: GraphEdge, selectedId: string): number {
  if (!selectedId) return edge.type === 'explicit' ? 0.75 : 0.25
  return edge.source === selectedId || edge.target === selectedId ? 0.95 : 0.08
}

function nodeFill(node: PositionedNode, selectedId: string): string {
  if (selectedId && node.id === selectedId) return '#0f172a'
  if (node.node_type === 'entity') return '#0f766e'
  if (node.node_type === 'decision') return '#7c3aed'
  if (node.node_type === 'module') return '#2563eb'
  if (node.node_type === 'error_pattern') return '#dc2626'
  return node.degree > 0 ? '#2563eb' : '#cbd5e1'
}

function labelVisible(node: PositionedNode, selectedId: string): boolean {
  return node.id === selectedId || node.degree >= 3
}

export default function KnowledgeGraphPage() {
  const { data, isLoading, error } = useWikiGraph()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filter, setFilter] = useState<GraphFilter>('connected')
  const requestedNodeId = searchParams.get('node') ?? ''
  const [selectedId, setSelectedId] = useState(requestedNodeId)

  const nodes: GraphNode[] = data?.nodes ?? []
  const edges: GraphEdge[] = data?.edges ?? []
  const graph = buildGraphState(nodes, edges, filter)
  const nodeMap = useMemo(() => new Map(graph.visibleNodes.map(node => [node.id, node])), [graph.visibleNodes])
  const selectedNode = selectedId ? nodeMap.get(selectedId) : graph.visibleNodes[0]

  const selectNode = (nodeId: string) => {
    setSelectedId(nodeId)
    const next = new URLSearchParams(searchParams)
    next.set('node', nodeId)
    setSearchParams(next, { replace: true })
  }

  useEffect(() => {
    if (!requestedNodeId) return
    if (requestedNodeId !== selectedId) {
      setSelectedId(requestedNodeId)
    }
  }, [requestedNodeId, selectedId])

  useEffect(() => {
    if (graph.visibleNodes.length === 0) {
      if (selectedId) {
        setSelectedId('')
      }
      return
    }
    if (!selectedId || !nodeMap.has(selectedId)) {
      selectNode(graph.visibleNodes[0].id)
    }
  }, [graph.visibleNodes, nodeMap, searchParams, selectedId, setSearchParams])

  const selectedNeighbors = graph.visibleEdges
    .filter(edge => edge.source === selectedNode?.id || edge.target === selectedNode?.id)
    .map(edge => {
      const neighborId = edge.source === selectedNode?.id ? edge.target : edge.source
      return {
        edge,
        neighbor: nodeMap.get(neighborId),
      }
    })
    .filter(item => item.neighbor)
    .sort((left, right) => (right.neighbor?.degree ?? 0) - (left.neighbor?.degree ?? 0))

  const explicitCount = edges.filter(edge => edge.type === 'explicit').length
  const inferredCount = edges.filter(edge => edge.type === 'inferred').length

  return (
    <div className="space-y-4" data-testid="knowledge-graph-page">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="page-title">知识图谱</h1>
          <p className="mt-1 text-sm text-gray-500">
            先用显式 wiki 链接建主干，再用同项目 / 标签相似度补轻量推断关系，避免 0 边图谱完全不可读。
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
          <span className="rounded-full bg-slate-100 px-3 py-1.5">{nodes.length} 节点</span>
          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-blue-700">{explicitCount} 显式关系</span>
          <span className="rounded-full bg-slate-100 px-3 py-1.5">{inferredCount} 推断关系</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {([
          ['connected', '仅看已连接'],
          ['all', '全部页面'],
          ['explicit', '仅显式关系'],
          ['inferred', '仅推断关系'],
        ] as Array<[GraphFilter, string]>).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={filter === value ? 'btn' : 'btn btn-outline'}
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading && <LoadingSpinner text="加载知识图谱..." />}
      {error && <ErrorAlert message="知识图谱加载失败" />}

      {!isLoading && !error && graph.visibleNodes.length === 0 && (
        <div className="rounded-xl border bg-white p-10 text-center text-gray-500">
          <div className="text-4xl">🕸️</div>
          <p className="mt-3">当前没有可展示的关系。</p>
          <p className="mt-2 text-sm text-gray-400">
            先用 <code>amem wiki-link from-topic to-topic</code> 建显式链接，或给页面补充 `project` / `tags` 元数据。
          </p>
        </div>
      )}

      {!isLoading && !error && graph.visibleNodes.length > 0 && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="overflow-auto rounded-xl border border-gray-100 bg-white p-4">
            <svg
              width={SVG_WIDTH}
              height={graph.height}
              viewBox={`0 0 ${SVG_WIDTH} ${graph.height}`}
              className="min-w-[960px]"
              data-testid="graph-canvas"
            >
              {graph.projectOrder.map((project, index) => {
                const x = 40 + index * graph.laneWidth
                return (
                  <g key={project}>
                    <rect
                      x={x}
                      y={44}
                      width={graph.laneWidth - 16}
                      height={graph.height - 70}
                      rx={18}
                      fill={index % 2 === 0 ? '#f8fafc' : '#f1f5f9'}
                    />
                    <text x={x + 18} y={30} fill="#475569" fontSize="12" fontWeight="600">
                      {project === 'unassigned' ? '未归类项目' : project}
                    </text>
                  </g>
                )
              })}

              {graph.visibleEdges.map(edge => {
                const source = nodeMap.get(edge.source)
                const target = nodeMap.get(edge.target)
                if (!source || !target) return null
                return (
                  <line
                    key={`${edge.source}-${edge.target}-${edge.type}`}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={edgeColor(edge)}
                    strokeOpacity={edgeOpacity(edge, selectedNode?.id ?? '')}
                    strokeWidth={edge.type === 'explicit' ? 1.8 : 1}
                  />
                )
              })}

              {graph.visibleNodes.map(node => (
                <g
                  key={node.id}
                  onClick={() => selectNode(node.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={selectedNode?.id === node.id ? 7 : Math.max(4, Math.min(8, 4 + node.degree * 0.7))}
                    fill={nodeFill(node, selectedNode?.id ?? '')}
                    stroke={selectedNode?.id === node.id ? '#93c5fd' : '#ffffff'}
                    strokeWidth={selectedNode?.id === node.id ? 3 : 1.5}
                  />
                  {labelVisible(node, selectedNode?.id ?? '') && (
                    <text x={node.x + 12} y={node.y + 4} fill="#0f172a" fontSize="11" fontWeight="500">
                      {(node.title || node.id).length > 28 ? `${(node.title || node.id).slice(0, 26)}…` : (node.title || node.id)}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-gray-100 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">阅读提示</h2>
              <div className="mt-3 space-y-2 text-sm text-slate-500">
                <p><span className="font-medium text-teal-700">青色节点</span> 是实体。</p>
                <p><span className="font-medium text-violet-700">紫色节点</span> 是决策。</p>
                <p><span className="font-medium text-blue-600">蓝色节点</span> 是模块。</p>
                <p><span className="font-medium text-red-600">红色节点</span> 是错误模式。</p>
                <p>点击节点后，只强调当前概念的邻居；页面本身退到右侧卡片里的阅读入口。</p>
              </div>
            </div>

            {selectedNode && (
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">{selectedNode.title || selectedNode.id}</h2>
                    <p className="mt-1 text-xs text-slate-500">
                      {(selectedNode.node_type || 'entity')} · {selectedNode.project || '未归类项目'}
                    </p>
                  </div>
                  {selectedNode.primary_topic ? (
                    <Link
                      to={`/wiki/${encodeURIComponent(selectedNode.primary_topic)}`}
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
                    <div className="mt-1 font-semibold text-slate-900">{selectedNode.degree}</div>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-3 py-2">
                    <div className="text-xs text-slate-400">字数</div>
                    <div className="mt-1 font-semibold text-slate-900">{selectedNode.word_count ?? 0}</div>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-3 py-2">
                    <div className="text-xs text-slate-400">关联页面数</div>
                    <div className="mt-1 font-semibold text-slate-900">{selectedNode.topic_count ?? 0}</div>
                  </div>
                </div>

                <div className="mt-4">
                  <h3 className="text-sm font-semibold text-slate-900">关联页面</h3>
                  <div className="mt-3 space-y-3">
                    {selectedNeighbors.length === 0 && (
                      <p className="text-sm text-slate-400">当前页面还没有稳定关系，建议补 `links` 或更准确的标签。</p>
                    )}
                    {selectedNeighbors.map(({ edge, neighbor }) => (
                      <div key={`${selectedNode.id}-${neighbor?.id}`} className="rounded-lg border border-slate-200 px-3 py-3">
                        <div className="flex items-center justify-between gap-2">
                          {neighbor?.primary_topic ? (
                            <Link to={`/wiki/${encodeURIComponent(neighbor.primary_topic)}`} className="font-medium text-slate-900 hover:text-blue-600 hover:underline">
                              {neighbor.title || neighbor.id}
                            </Link>
                          ) : (
                            <span className="font-medium text-slate-900">{neighbor?.title || neighbor?.id}</span>
                          )}
                          <span className={edge.type === 'explicit' ? 'badge badge-blue' : 'badge badge-gray'}>
                            {edge.type === 'explicit' ? '显式' : '推断'}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">
                          {edge.type === 'explicit'
                            ? '来自页面 frontmatter.links 的明确引用。'
                            : `推断强度 ${edge.weight ?? 0}，建议人工确认后补成显式 links。`}
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
    </div>
  )
}
