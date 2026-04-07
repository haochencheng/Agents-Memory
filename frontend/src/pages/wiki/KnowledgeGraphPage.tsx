import { useEffect, useRef } from 'react'
import { useWikiGraph } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

interface GraphNode {
  id: string
  title?: string
}
interface GraphEdge {
  source: string
  target: string
}

function ForceGraphCanvas({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width
    const H = canvas.height

    // Simple static layout (circular)
    const n = nodes.length
    const positions: Record<string, { x: number; y: number }> = {}
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / n
      positions[node.id] = {
        x: W / 2 + (W * 0.35) * Math.cos(angle),
        y: H / 2 + (H * 0.35) * Math.sin(angle),
      }
    })

    ctx.clearRect(0, 0, W, H)

    // Draw edges
    ctx.strokeStyle = '#cbd5e1'
    ctx.lineWidth = 1
    edges.forEach(e => {
      const s = positions[e.source]
      const t = positions[e.target]
      if (!s || !t) return
      ctx.beginPath()
      ctx.moveTo(s.x, s.y)
      ctx.lineTo(t.x, t.y)
      ctx.stroke()
    })

    // Draw nodes
    nodes.forEach(node => {
      const p = positions[node.id]
      if (!p) return
      ctx.beginPath()
      ctx.arc(p.x, p.y, 6, 0, 2 * Math.PI)
      ctx.fillStyle = '#3b82f6'
      ctx.fill()
      ctx.fillStyle = '#1e293b'
      ctx.font = '11px system-ui'
      ctx.fillText(node.id.length > 16 ? node.id.slice(0, 14) + '…' : node.id, p.x + 9, p.y + 4)
    })
  }, [nodes, edges])

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={500}
      className="w-full rounded-xl border border-gray-100 bg-gray-50"
      data-testid="graph-canvas"
    />
  )
}

export default function KnowledgeGraphPage() {
  const { data, isLoading, error } = useWikiGraph()

  if (isLoading) return <LoadingSpinner text="加载知识图谱..." />
  if (error) return <ErrorAlert message="知识图谱加载失败" />

  const nodes: GraphNode[] = data?.nodes ?? []
  const edges: GraphEdge[] = data?.edges ?? []

  return (
    <div className="space-y-4" data-testid="knowledge-graph-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">知识图谱</h1>
        <span className="text-sm text-gray-500">{nodes.length} 节点 · {edges.length} 连接</span>
      </div>

      {nodes.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
          <div className="text-5xl mb-3">🕸️</div>
          <p>暂无图谱数据</p>
        </div>
      ) : (
        <ForceGraphCanvas nodes={nodes} edges={edges} />
      )}
    </div>
  )
}
