import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import MemoryRecords from '@/pages/dashboard/MemoryRecords'

const useErrorsMock = vi.fn()
const useRulesMock = vi.fn()
const useSearchResultsMock = vi.fn()
const useWikiGraphMock = vi.fn()

vi.mock('@/api/useMemory', () => ({
  useErrors: (...args: unknown[]) => useErrorsMock(...args),
  useRules: (...args: unknown[]) => useRulesMock(...args),
  useSearchResults: (...args: unknown[]) => useSearchResultsMock(...args),
}))

vi.mock('@/api/useWiki', () => ({
  useWikiGraph: (...args: unknown[]) => useWikiGraphMock(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <MemoryRecords />
    </MemoryRouter>,
  )
}

describe('MemoryRecords page', () => {
  beforeEach(() => {
    useErrorsMock.mockReset()
    useRulesMock.mockReset()
    useSearchResultsMock.mockReset()
    useWikiGraphMock.mockReset()

    useErrorsMock.mockImplementation((params?: { page?: number; pageSize?: number }) => {
      const page = params?.page ?? 1
      if (page === 2) {
        return {
          data: {
            errors: [
              {
                id: 'ERR-3',
                title: 'Third error',
                project: 'synapse-network',
                created_at: '2026-04-13',
                severity: 'high',
                status: 'open',
              },
            ],
            total: 3,
            page: 2,
            page_size: 2,
            total_pages: 2,
          },
          isLoading: false,
          error: null,
        }
      }
      return {
        data: {
          errors: [
            {
              id: 'ERR-1',
              title: 'First error',
              project: 'synapse-network',
              created_at: '2026-04-13',
              severity: 'high',
              status: 'open',
            },
            {
              id: 'ERR-2',
              title: 'Second error',
              project: 'synapse-network',
              created_at: '2026-04-13',
              severity: 'high',
              status: 'open',
            },
          ],
          total: 3,
          page: 1,
          page_size: 2,
          total_pages: 2,
        },
        isLoading: false,
        error: null,
      }
    })

    useRulesMock.mockReturnValue({
      data: { rules: [] },
      isLoading: false,
      error: null,
    })

    useSearchResultsMock.mockImplementation((query?: string) => {
      if (query === 'jwt') {
        return {
          data: {
            query: 'jwt',
            mode: 'hybrid',
            total: 1,
            results: [
              {
                type: 'wiki',
                id: 'auth-design',
                title: 'Auth Design',
                snippet: 'JWT refresh details',
                score: 0.9,
                rerank_boost: 0.2,
                rerank_reasons: [],
                matched_concepts: [],
              },
            ],
          },
          isLoading: false,
        }
      }
      return {
        data: { query: query ?? '', mode: 'hybrid', total: 0, results: [] },
        isLoading: false,
      }
    })

    useWikiGraphMock.mockReturnValue({
      data: { nodes: [], edges: [] },
    })
  })

  it('renders paginated errors list state and moves pages', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(screen.getByTestId('errors-pagination-summary')).toHaveTextContent('第 1 / 2 页，每页 2 条')
    expect(screen.getByText('First error')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '下一页' }))

    expect(screen.getByText('Third error')).toBeInTheDocument()
    expect(screen.getByTestId('errors-pagination-summary')).toHaveTextContent('第 2 / 2 页，每页 2 条')
  })

  it('submits unified search only when clicking search button', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByTestId('memory-search-input'), 'jwt')
    expect(useSearchResultsMock).toHaveBeenLastCalledWith('')
    expect(screen.queryByText('Auth Design')).not.toBeInTheDocument()

    await user.click(screen.getByTestId('memory-search-submit'))

    expect(useSearchResultsMock).toHaveBeenLastCalledWith('jwt')
    expect(screen.getByText('Auth Design')).toBeInTheDocument()
  })
})
