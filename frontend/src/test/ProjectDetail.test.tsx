import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProjectDetail from '@/pages/dashboard/ProjectDetail'

const useProjectStatsMock = vi.fn()
const useProjectWikiNavMock = vi.fn()

vi.mock('@/api/useProjects', () => ({
  useProjectStats: (...args: unknown[]) => useProjectStatsMock(...args),
  useProjectWikiNav: (...args: unknown[]) => useProjectWikiNavMock(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/synapse-network']}>
      <Routes>
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/wiki/:topic" element={<div data-testid="wiki-topic-route">wiki detail</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProjectDetail page', () => {
  beforeEach(() => {
    useProjectStatsMock.mockReset()
    useProjectWikiNavMock.mockReset()

    useProjectStatsMock.mockReturnValue({
      data: {
        id: 'synapse-network',
        health: 'ok',
        wiki_count: 127,
        error_count: 0,
        checklist_done: 0,
        ingest_count: 127,
        last_error: '',
        last_ingest: '2026-04-08T00:00:00Z',
      },
      isLoading: false,
      error: null,
    })

    useProjectWikiNavMock.mockReturnValue({
      data: {
        project_id: 'synapse-network',
        total_topics: 3,
        items: [
          {
            topic: 'synapse-network-readme',
            title: 'Synapse Network Readme',
            source_path: 'README.md',
            nav_path: 'Root Docs',
            source_group: 'Root Docs',
            document_role: 'root-doc',
            updated_at: '2026-04-08',
            word_count: 200,
          },
          {
            topic: 'synapse-network-docs-architecture',
            title: 'Synapse Network Docs Architecture',
            source_path: 'docs/architecture/README.md',
            nav_path: 'docs/architecture',
            source_group: 'Architecture',
            document_role: 'architecture',
            updated_at: '2026-04-08',
            word_count: 300,
          },
          {
            topic: 'synapse-network-docs-plan',
            title: 'Synapse Network Plan',
            source_path: 'docs/plans/plan.md',
            nav_path: 'docs/plans',
            source_group: 'Plans',
            document_role: 'plan',
            updated_at: '2026-04-08',
            word_count: 180,
          },
        ],
        tree: [
          {
            key: 'Root Docs',
            label: 'Root Docs',
            path: 'Root Docs',
            depth: 0,
            item_count: 1,
            topics: [
              {
                topic: 'synapse-network-readme',
                title: 'Synapse Network Readme',
                source_path: 'README.md',
                nav_path: 'Root Docs',
                source_group: 'Root Docs',
                document_role: 'root-doc',
                updated_at: '2026-04-08',
                word_count: 200,
              },
            ],
            children: [],
          },
          {
            key: 'docs',
            label: 'docs',
            path: 'docs',
            depth: 0,
            item_count: 2,
            topics: [],
            children: [
              {
                key: 'docs/architecture',
                label: 'Architecture',
                path: 'docs/architecture',
                depth: 1,
                item_count: 1,
                topics: [
                  {
                    topic: 'synapse-network-docs-architecture',
                    title: 'Synapse Network Docs Architecture',
                    source_path: 'docs/architecture/README.md',
                    nav_path: 'docs/architecture',
                    source_group: 'Architecture',
                    document_role: 'architecture',
                    updated_at: '2026-04-08',
                    word_count: 300,
                  },
                ],
                children: [],
              },
              {
                key: 'docs/plans',
                label: 'Plans',
                path: 'docs/plans',
                depth: 1,
                item_count: 1,
                topics: [
                  {
                    topic: 'synapse-network-docs-plan',
                    title: 'Synapse Network Plan',
                    source_path: 'docs/plans/plan.md',
                    nav_path: 'docs/plans',
                    source_group: 'Plans',
                    document_role: 'plan',
                    updated_at: '2026-04-08',
                    word_count: 180,
                  },
                ],
                children: [],
              },
            ],
          },
        ],
        groups: [
          {
            key: 'Architecture',
            label: 'Architecture',
            item_count: 1,
            topics: [
              {
                topic: 'synapse-network-docs-architecture',
                title: 'Synapse Network Docs Architecture',
                source_path: 'docs/architecture/README.md',
                nav_path: 'docs/architecture',
                source_group: 'Architecture',
                document_role: 'architecture',
                updated_at: '2026-04-08',
                word_count: 300,
              },
            ],
          },
          {
            key: 'Plans',
            label: 'Plans',
            item_count: 1,
            topics: [
              {
                topic: 'synapse-network-docs-plan',
                title: 'Synapse Network Plan',
                source_path: 'docs/plans/plan.md',
                nav_path: 'docs/plans',
                source_group: 'Plans',
                document_role: 'plan',
                updated_at: '2026-04-08',
                word_count: 180,
              },
            ],
          },
          {
            key: 'Root Docs',
            label: 'Root Docs',
            item_count: 1,
            topics: [
              {
                topic: 'synapse-network-readme',
                title: 'Synapse Network Readme',
                source_path: 'README.md',
                nav_path: 'Root Docs',
                source_group: 'Root Docs',
                document_role: 'root-doc',
                updated_at: '2026-04-08',
                word_count: 200,
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    })
  })

  it('renders tree view by default', () => {
    renderPage()
    const treeView = screen.getByTestId('project-wiki-tree-view')

    expect(treeView).toBeInTheDocument()
    expect(within(treeView).getAllByText('Root Docs').length).toBeGreaterThan(0)
    expect(within(treeView).getByText('Synapse Network Plan')).toBeInTheDocument()
  })

  it('switches to domain view', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Domain' }))

    const domainView = screen.getByTestId('project-wiki-domain-view')

    expect(domainView).toBeInTheDocument()
    expect(within(domainView).getByText('Architecture')).toBeInTheDocument()
    expect(screen.getAllByTestId('project-domain-group')).toHaveLength(3)
  })

  it('renders a collapsible explorer sidebar and opens wiki detail from file items', async () => {
    const user = userEvent.setup()
    renderPage()

    const sidebar = screen.getByTestId('project-wiki-sidebar')
    const rootButtons = within(sidebar).getAllByTestId('project-explorer-node')

    expect(within(sidebar).getByText('Project Explorer')).toBeInTheDocument()
    expect(within(sidebar).getByText('Synapse Network Docs Architecture')).toBeInTheDocument()

    await user.click(rootButtons[1])
    expect(within(sidebar).queryByText('Synapse Network Docs Architecture')).not.toBeInTheDocument()

    await user.click(within(sidebar).getAllByTestId('project-explorer-node')[1])
    expect(within(sidebar).getByText('Synapse Network Docs Architecture')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Domain' }))
    expect(screen.getByTestId('project-wiki-domain-view')).toBeInTheDocument()

    await user.click(within(sidebar).getByRole('link', { name: /Synapse Network Plan/i }))
    expect(screen.getByTestId('wiki-topic-route')).toBeInTheDocument()
  })
})