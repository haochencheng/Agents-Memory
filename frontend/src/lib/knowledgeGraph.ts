export type GraphRelationFilter = 'all' | 'explicit' | 'inferred'
export type GraphExplorerView = 'schema' | 'explore' | 'table'

export interface KnowledgeGraphNode {
  id: string
  title?: string
  node_type?: string
  project?: string
  word_count?: number
  tags?: string[]
  primary_topic?: string
  topic_count?: number
}

export interface KnowledgeGraphEdge {
  source: string
  target: string
  type?: string
  weight?: number
}

export interface GraphFilters {
  project: string
  nodeType: string
  relation: GraphRelationFilter
  query: string
}

export interface GraphNodeWithDegree extends KnowledgeGraphNode {
  degree: number
}

export interface PositionedGraphNode extends GraphNodeWithDegree {
  x: number
  y: number
  distance: number
}

export interface GraphSchemaTypeSummary {
  key: string
  label: string
  count: number
  connectedCount: number
}

export interface GraphSchemaProjectSummary {
  project: string
  total: number
  connected: number
  breakdown: Record<string, number>
}

export interface GraphSchemaRelationSummary {
  key: string
  label: string
  count: number
}

export interface GraphSchemaSummary {
  nodeTypes: GraphSchemaTypeSummary[]
  relationTypes: GraphSchemaRelationSummary[]
  projects: GraphSchemaProjectSummary[]
}

export interface ExploreNeighbor {
  edge: KnowledgeGraphEdge
  node: GraphNodeWithDegree
}

export interface GraphTableRow extends GraphNodeWithDegree {
  hasPrimaryTopic: boolean
}

export interface GraphExploreModel {
  focusNode: GraphNodeWithDegree | null
  candidateNodes: GraphNodeWithDegree[]
  visibleNodes: PositionedGraphNode[]
  visibleEdges: KnowledgeGraphEdge[]
  neighbors: ExploreNeighbor[]
}

const SVG_WIDTH = 920
const SVG_HEIGHT = 620
const NODE_TYPE_ORDER = ['entity', 'decision', 'module', 'error_pattern'] as const
const NODE_TYPE_LABELS: Record<string, string> = {
  entity: '实体',
  decision: '决策',
  module: '模块',
  error_pattern: '错误模式',
}
const RELATION_LABELS: Record<string, string> = {
  explicit: '显式关系',
  inferred: '推断关系',
}

function nodeTypeRank(nodeType: string): number {
  const rank = NODE_TYPE_ORDER.indexOf(nodeType as (typeof NODE_TYPE_ORDER)[number])
  return rank >= 0 ? rank : NODE_TYPE_ORDER.length
}

function normalizedProject(value?: string): string {
  return value?.trim() || 'unassigned'
}

function normalizedNodeType(value?: string): string {
  return value?.trim() || 'other'
}

function normalizeText(value: string): string {
  return value.trim().toLowerCase()
}

function matchesRelation(edge: KnowledgeGraphEdge, relation: GraphRelationFilter): boolean {
  if (relation === 'all') return true
  return (edge.type || '') === relation
}

function matchesNode(node: KnowledgeGraphNode, filters: GraphFilters): boolean {
  if (filters.project !== 'all' && normalizedProject(node.project) !== filters.project) {
    return false
  }
  if (filters.nodeType !== 'all' && normalizedNodeType(node.node_type) !== filters.nodeType) {
    return false
  }
  if (!filters.query.trim()) return true

  const haystack = [
    node.id,
    node.title || '',
    node.project || '',
    node.node_type || '',
    node.primary_topic || '',
    ...(node.tags || []),
  ]
    .join(' ')
    .toLowerCase()
  return haystack.includes(normalizeText(filters.query))
}

function buildDegreeMap(nodes: KnowledgeGraphNode[], edges: KnowledgeGraphEdge[]): Map<string, number> {
  const degreeMap = new Map<string, number>()
  nodes.forEach(node => degreeMap.set(node.id, 0))
  edges.forEach(edge => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  })
  return degreeMap
}

function sortNodes(nodes: GraphNodeWithDegree[]): GraphNodeWithDegree[] {
  return [...nodes].sort((left, right) => {
    const degreeDelta = right.degree - left.degree
    if (degreeDelta !== 0) return degreeDelta
    const projectDelta = normalizedProject(left.project).localeCompare(normalizedProject(right.project))
    if (projectDelta !== 0) return projectDelta
    const typeDelta = nodeTypeRank(normalizedNodeType(left.node_type)) - nodeTypeRank(normalizedNodeType(right.node_type))
    if (typeDelta !== 0) return typeDelta
    return (left.title || left.id).localeCompare(right.title || right.id)
  })
}

export function buildGraphFilters(filters?: Partial<GraphFilters>): GraphFilters {
  return {
    project: filters?.project || 'all',
    nodeType: filters?.nodeType || 'all',
    relation: filters?.relation || 'all',
    query: filters?.query || '',
  }
}

export function buildFilterOptions(nodes: KnowledgeGraphNode[]) {
  const projects = Array.from(new Set(nodes.map(node => normalizedProject(node.project)))).sort((left, right) =>
    left.localeCompare(right),
  )
  const nodeTypes = Array.from(new Set(nodes.map(node => normalizedNodeType(node.node_type)))).sort((left, right) =>
    nodeTypeRank(left) - nodeTypeRank(right) || left.localeCompare(right),
  )
  return {
    projects,
    nodeTypes,
  }
}

export function buildFilteredGraph(
  nodes: KnowledgeGraphNode[],
  edges: KnowledgeGraphEdge[],
  filters?: Partial<GraphFilters>,
) {
  const resolvedFilters = buildGraphFilters(filters)
  const relationEdges = edges.filter(edge => matchesRelation(edge, resolvedFilters.relation))
  const nodeIdsInEdges = new Set<string>()
  relationEdges.forEach(edge => {
    nodeIdsInEdges.add(edge.source)
    nodeIdsInEdges.add(edge.target)
  })

  const filteredNodes = nodes.filter(node => matchesNode(node, resolvedFilters))
  const filteredIds = new Set(filteredNodes.map(node => node.id))
  const visibleEdges = relationEdges.filter(edge => filteredIds.has(edge.source) && filteredIds.has(edge.target))
  const degreeMap = buildDegreeMap(filteredNodes, visibleEdges)
  const visibleNodes = sortNodes(
    filteredNodes.map(node => ({
      ...node,
      degree: degreeMap.get(node.id) ?? 0,
    })),
  )

  return {
    filters: resolvedFilters,
    filteredNodes: visibleNodes,
    filteredEdges: visibleEdges,
    connectedNodeIds: nodeIdsInEdges,
    degreeMap,
  }
}

function buildNodeMap(nodes: GraphNodeWithDegree[]): Map<string, GraphNodeWithDegree> {
  return new Map(nodes.map(node => [node.id, node]))
}

function buildAdjacency(edges: KnowledgeGraphEdge[]): Map<string, Set<string>> {
  const adjacency = new Map<string, Set<string>>()
  edges.forEach(edge => {
    adjacency.set(edge.source, adjacency.get(edge.source) ?? new Set<string>())
    adjacency.set(edge.target, adjacency.get(edge.target) ?? new Set<string>())
    adjacency.get(edge.source)?.add(edge.target)
    adjacency.get(edge.target)?.add(edge.source)
  })
  return adjacency
}

function computeDistances(edges: KnowledgeGraphEdge[], focusId: string, depth: number): Map<string, number> {
  const adjacency = buildAdjacency(edges)
  const distances = new Map<string, number>([[focusId, 0]])
  const queue: Array<{ id: string; distance: number }> = [{ id: focusId, distance: 0 }]

  while (queue.length > 0) {
    const current = queue.shift()
    if (!current) continue
    if (current.distance >= depth) continue

    const neighbors = adjacency.get(current.id) ?? new Set<string>()
    neighbors.forEach(neighborId => {
      if (distances.has(neighborId)) return
      distances.set(neighborId, current.distance + 1)
      queue.push({ id: neighborId, distance: current.distance + 1 })
    })
  }

  return distances
}

function radialLayout(
  nodes: GraphNodeWithDegree[],
  edges: KnowledgeGraphEdge[],
  focusId: string,
  depth: number,
): PositionedGraphNode[] {
  const distances = computeDistances(edges, focusId, depth)
  const focusNode = nodes.find(node => node.id === focusId)
  if (!focusNode) return []

  const byDistance = new Map<number, GraphNodeWithDegree[]>()
  nodes.forEach(node => {
    const distance = distances.get(node.id)
    if (distance === undefined) return
    byDistance.set(distance, [...(byDistance.get(distance) ?? []), node])
  })

  const positioned: PositionedGraphNode[] = [
    {
      ...focusNode,
      x: SVG_WIDTH / 2,
      y: SVG_HEIGHT / 2,
      distance: 0,
    },
  ]

  Array.from(byDistance.entries())
    .filter(([distance]) => distance > 0)
    .sort((left, right) => left[0] - right[0])
    .forEach(([distance, group]) => {
      const ordered = sortNodes(group)
      const radius = distance === 1 ? 170 : 280
      ordered.forEach((node, index) => {
        const angle = (Math.PI * 2 * index) / ordered.length - Math.PI / 2
        positioned.push({
          ...node,
          x: Math.round(SVG_WIDTH / 2 + Math.cos(angle) * radius),
          y: Math.round(SVG_HEIGHT / 2 + Math.sin(angle) * radius),
          distance,
        })
      })
    })

  return positioned
}

export function buildSchemaSummary(nodes: KnowledgeGraphNode[], edges: KnowledgeGraphEdge[]): GraphSchemaSummary {
  const degreeMap = buildDegreeMap(nodes, edges)
  const relationTypes = ['explicit', 'inferred']

  const nodeTypes = Array.from(
    new Set(nodes.map(node => normalizedNodeType(node.node_type)).concat([...NODE_TYPE_ORDER])),
  )
    .filter(nodeType => nodes.some(node => normalizedNodeType(node.node_type) === nodeType))
    .sort((left, right) => nodeTypeRank(left) - nodeTypeRank(right) || left.localeCompare(right))
    .map(nodeType => {
      const matching = nodes.filter(node => normalizedNodeType(node.node_type) === nodeType)
      return {
        key: nodeType,
        label: NODE_TYPE_LABELS[nodeType] || nodeType,
        count: matching.length,
        connectedCount: matching.filter(node => (degreeMap.get(node.id) ?? 0) > 0).length,
      }
    })

  const projects = Array.from(new Set(nodes.map(node => normalizedProject(node.project))))
    .sort((left, right) => left.localeCompare(right))
    .map(project => {
      const matching = nodes.filter(node => normalizedProject(node.project) === project)
      const breakdown: Record<string, number> = {}
      matching.forEach(node => {
        const nodeType = normalizedNodeType(node.node_type)
        breakdown[nodeType] = (breakdown[nodeType] ?? 0) + 1
      })
      return {
        project,
        total: matching.length,
        connected: matching.filter(node => (degreeMap.get(node.id) ?? 0) > 0).length,
        breakdown,
      }
    })

  return {
    nodeTypes,
    relationTypes: relationTypes.map(relationType => ({
      key: relationType,
      label: RELATION_LABELS[relationType],
      count: edges.filter(edge => (edge.type || '') === relationType).length,
    })),
    projects,
  }
}

export function buildExploreModel(
  nodes: KnowledgeGraphNode[],
  edges: KnowledgeGraphEdge[],
  filters: Partial<GraphFilters>,
  selectedId: string,
  depth: 1 | 2,
): GraphExploreModel {
  const filtered = buildFilteredGraph(nodes, edges, filters)
  const focusNode =
    filtered.filteredNodes.find(node => node.id === selectedId) ??
    filtered.filteredNodes[0] ??
    null

  if (!focusNode) {
    return {
      focusNode: null,
      candidateNodes: [],
      visibleNodes: [],
      visibleEdges: [],
      neighbors: [],
    }
  }

  const distances = computeDistances(filtered.filteredEdges, focusNode.id, depth)
  const visibleIds = new Set(distances.keys())
  const visibleNodes = radialLayout(
    filtered.filteredNodes.filter(node => visibleIds.has(node.id)),
    filtered.filteredEdges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    focusNode.id,
    depth,
  )
  const nodeMap = buildNodeMap(filtered.filteredNodes)
  const neighbors = filtered.filteredEdges
    .filter(edge => edge.source === focusNode.id || edge.target === focusNode.id)
    .map(edge => {
      const neighborId = edge.source === focusNode.id ? edge.target : edge.source
      return {
        edge,
        node: nodeMap.get(neighborId),
      }
    })
    .filter((item): item is ExploreNeighbor => Boolean(item.node))
    .sort((left, right) => right.node.degree - left.node.degree)

  return {
    focusNode,
    candidateNodes: filtered.filteredNodes.slice(0, 18),
    visibleNodes,
    visibleEdges: filtered.filteredEdges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    neighbors,
  }
}

export function buildTableRows(
  nodes: KnowledgeGraphNode[],
  edges: KnowledgeGraphEdge[],
  filters: Partial<GraphFilters>,
): GraphTableRow[] {
  const filtered = buildFilteredGraph(nodes, edges, filters)
  return filtered.filteredNodes.map(node => ({
    ...node,
    hasPrimaryTopic: Boolean(node.primary_topic?.trim()),
  }))
}

export function formatNodeType(nodeType?: string): string {
  return NODE_TYPE_LABELS[normalizedNodeType(nodeType)] || normalizedNodeType(nodeType)
}

export function formatProject(project?: string): string {
  return normalizedProject(project) === 'unassigned' ? '未归类项目' : normalizedProject(project)
}

export function graphCanvasSize() {
  return {
    width: SVG_WIDTH,
    height: SVG_HEIGHT,
  }
}

export function edgeColor(edge: KnowledgeGraphEdge): string {
  return edge.type === 'explicit' ? '#2563eb' : '#94a3b8'
}
