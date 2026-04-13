import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Checks from '@/pages/dashboard/Checks'

vi.mock('@/api/useScheduler', () => ({
  useChecks: () => ({
    data: {
      checks: [
        {
          id: 'CHK-1',
          task_id: 'task-1',
          task_name: 'nightly-check-docs',
          project: 'synapse-network',
          check_type: 'docs',
          status: 'fail',
          run_at: '2026-04-13T02:00:00+08:00',
          duration_ms: 42,
          summary: 'FAIL:docs_entrypoint',
          details: ['[FAIL] docs_entrypoint: missing docs/README.md'],
        },
      ],
      total: 1,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

describe('Checks page', () => {
  it('renders structured check results from the API envelope', () => {
    render(
      <MemoryRouter>
        <Checks />
      </MemoryRouter>,
    )

    expect(screen.getByText('nightly-check-docs')).toBeInTheDocument()
    expect(screen.getByText(/synapse-network · docs-check/i)).toBeInTheDocument()
    expect(screen.getByText(/\[FAIL\] docs_entrypoint/i)).toBeInTheDocument()
  })
})
