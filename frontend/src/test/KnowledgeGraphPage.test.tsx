import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import KnowledgeGraphPage from '@/pages/wiki/KnowledgeGraphPage'

const useWikiGraphMock = vi.fn()

vi.mock('@/api/useWiki', () => ({
  useWikiGraph: (...args: unknown[]) => useWikiGraphMock(...args),
}))

function renderPage(initialEntry = '/wiki/graph') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <KnowledgeGraphPage />
    </MemoryRouter>,
  )
}

describe('KnowledgeGraphPage', () => {
  beforeEach(() => {
    useWikiGraphMock.mockReset()
    useWikiGraphMock.mockReturnValue({
      data: {
        nodes: [
          {
            id: 'entity:synapse-network',
            title: 'Synapse Network',
            node_type: 'entity',
            project: 'synapse-network',
            topic_count: 2,
          },
          {
            id: 'decision:auth-design',
            title: 'Auth Design',
            node_type: 'decision',
            project: 'synapse-network',
            primary_topic: 'auth-design',
            topic_count: 1,
          },
          {
            id: 'module:billing-recharge',
            title: 'Billing Recharge',
            node_type: 'module',
            project: 'synapse-network',
            primary_topic: 'billing-recharge',
            topic_count: 1,
          },
          {
            id: 'error_pattern:token-refresh-loop',
            title: 'Token Refresh Loop',
            node_type: 'error_pattern',
            project: 'synapse-network-growing',
            topic_count: 1,
          },
        ],
        edges: [
          { source: 'entity:synapse-network', target: 'decision:auth-design', type: 'explicit', weight: 1 },
          { source: 'decision:auth-design', target: 'module:billing-recharge', type: 'explicit', weight: 1 },
          { source: 'decision:auth-design', target: 'error_pattern:token-refresh-loop', type: 'inferred', weight: 0.6 },
        ],
      },
      isLoading: false,
      error: null,
    })
  })

  it('renders schema explorer by default', () => {
    renderPage()

    const schemaView = screen.getByTestId('graph-schema-view')

    expect(schemaView).toBeInTheDocument()
    expect(within(schemaView).getByText('Project Schema Explorer')).toBeInTheDocument()
    expect(within(schemaView).getByTestId('graph-schema-table')).toBeInTheDocument()
    expect(within(schemaView).getAllByText('决策').length).toBeGreaterThan(0)
  })

  it('opens explore view when node is provided in the url', async () => {
    renderPage('/wiki/graph?node=decision%3Aauth-design')

    const exploreView = await screen.findByTestId('graph-explore-view')

    expect(exploreView).toBeInTheDocument()
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    expect(screen.getAllByText('Auth Design').length).toBeGreaterThan(0)
    expect(screen.getByText('Local Graph Explorer')).toBeInTheDocument()
  })

  it('filters table explorer results by search text', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Table' }))
    await user.type(screen.getByTestId('knowledge-graph-search-input'), 'billing')

    const table = screen.getByTestId('graph-table')

    expect(within(table).getByText('Billing Recharge')).toBeInTheDocument()
    expect(within(table).queryByText('Auth Design')).not.toBeInTheDocument()
  })
})
