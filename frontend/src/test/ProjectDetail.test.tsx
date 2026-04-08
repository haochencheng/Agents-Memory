import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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
    expect(screen.getByTestId('project-wiki-tree-view')).toBeInTheDocument()
    expect(screen.getAllByText('Root Docs').length).toBeGreaterThan(0)
    expect(screen.getByText('Synapse Network Plan')).toBeInTheDocument()
  })

  it('switches to domain view', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Domain' }))

    expect(screen.getByTestId('project-wiki-domain-view')).toBeInTheDocument()
    expect(screen.getByText('Architecture')).toBeInTheDocument()
    expect(screen.getAllByTestId('project-domain-group')).toHaveLength(3)
  })
})