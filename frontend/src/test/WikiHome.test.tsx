import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import WikiHome from '@/pages/wiki/WikiHome'

const useWikiListMock = vi.fn()

vi.mock('@/api/useWiki', () => ({
  useWikiList: (...args: unknown[]) => useWikiListMock(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <WikiHome />
    </MemoryRouter>
  )
}

describe('WikiHome page', () => {
  beforeEach(() => {
    useWikiListMock.mockReset()
    useWikiListMock.mockImplementation((params?: { query?: string; page?: number; pageSize?: number }) => {
      const query = params?.query ?? ''
      const page = params?.page ?? 1

      if (query === '充值') {
        return {
          data: {
            topics: [
              {
                topic: 'billing-recharge',
                title: 'Billing Recharge',
                tags: ['billing'],
                word_count: 320,
                updated_at: '2026-04-08',
                project: 'synapse-network',
                source_path: 'docs/billing/recharge.md',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
            query,
          },
          isLoading: false,
          error: null,
        }
      }

      if (page === 2) {
        return {
          data: {
            topics: [
              {
                topic: 'topic-21',
                title: 'Topic 21',
                tags: ['docs'],
                word_count: 210,
                updated_at: '2026-04-08',
                project: 'demo',
                source_path: 'docs/topic-21.md',
              },
            ],
            total: 21,
            page: 2,
            page_size: 20,
            total_pages: 2,
            query,
          },
          isLoading: false,
          error: null,
        }
      }

      return {
        data: {
          topics: [
            {
              topic: 'topic-1',
              title: 'Topic 1',
              tags: ['docs'],
              word_count: 200,
              updated_at: '2026-04-08',
              project: 'demo',
              source_path: 'docs/topic-1.md',
            },
          ],
          total: 21,
          page: 1,
          page_size: 20,
          total_pages: 2,
          query,
        },
        isLoading: false,
        error: null,
      }
    })
  })

  it('renders paginated wiki index state', () => {
    renderPage()

    expect(screen.getByText('Wiki 知识库')).toBeInTheDocument()
    expect(screen.getByTestId('wiki-pagination-summary')).toHaveTextContent('第 1 / 2 页，每页 20 条')
    expect(screen.getByText('Topic 1')).toBeInTheDocument()
  })

  it('moves to next page', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '下一页' }))

    expect(screen.getByText('Topic 21')).toBeInTheDocument()
    expect(screen.getByTestId('wiki-pagination-summary')).toHaveTextContent('第 2 / 2 页，每页 20 条')
  })

  it('uses server-side query for wiki search', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByTestId('wiki-search-input'), '充值')
    expect(useWikiListMock).toHaveBeenLastCalledWith({ query: '', page: 1, pageSize: 20 })

    await user.click(screen.getByTestId('wiki-search-submit'))

    expect(screen.getByText('Billing Recharge')).toBeInTheDocument()
    expect(useWikiListMock).toHaveBeenLastCalledWith({ query: '充值', page: 1, pageSize: 20 })
  })
})
