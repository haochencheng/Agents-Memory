import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Scheduler from '@/pages/dashboard/Scheduler'

const mutateAsyncMock = vi.fn()
const deleteMutateMock = vi.fn()

vi.mock('@/api/useScheduler', () => ({
  useSchedulerTasks: () => ({
    data: { tasks: [] },
    isLoading: false,
    error: null,
  }),
  useCreateSchedulerTask: () => ({
    isPending: false,
    mutateAsync: mutateAsyncMock,
  }),
  useDeleteSchedulerTask: () => ({
    isPending: false,
    mutate: deleteMutateMock,
  }),
}))

vi.mock('@/api/useProjects', () => ({
  useProjects: () => ({
    data: {
      projects: [
        { id: 'synapse-network', name: 'synapse-network' },
        { id: 'synapse-network-growing', name: 'synapse-network-growing' },
      ],
    },
  }),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <Scheduler />
    </MemoryRouter>,
  )
}

describe('Scheduler page', () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset()
    deleteMutateMock.mockReset()
  })

  it('renders registered project dropdown and fixed check bundle badges', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '+ 新增任务' }))

    expect(screen.getByTestId('create-task-form')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'synapse-network' })).toBeInTheDocument()
    expect(screen.getByText('docs')).toBeInTheDocument()
    expect(screen.getByText('profile')).toBeInTheDocument()
    expect(screen.getByText('plan')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '创建 3 个检查任务' })).toBeInTheDocument()
  })

  it('submits bundled scheduler task creation for selected project', async () => {
    mutateAsyncMock.mockResolvedValue({ tasks: [] })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '+ 新增任务' }))
    await user.type(screen.getByPlaceholderText('nightly-check'), 'nightly-check')
    await user.selectOptions(screen.getByDisplayValue('synapse-network'), 'synapse-network-growing')
    await user.type(screen.getByPlaceholderText('0 2 * * *'), '0 2 * * *')
    await user.click(screen.getByRole('button', { name: '创建 3 个检查任务' }))

    expect(mutateAsyncMock).toHaveBeenCalledWith({
      name: 'nightly-check',
      project: 'synapse-network-growing',
      cron_expr: '0 2 * * *',
    })
  })
})
