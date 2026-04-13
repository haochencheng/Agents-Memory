import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Scheduler from '@/pages/dashboard/Scheduler'

const createMutateAsyncMock = vi.fn()
const deleteMutateMock = vi.fn()
const pauseMutateMock = vi.fn()
const resumeMutateMock = vi.fn()
const runMutateMock = vi.fn()
const useSchedulerTaskGroupsMock = vi.fn()

vi.mock('@/api/useScheduler', () => ({
  useSchedulerTaskGroups: (...args: unknown[]) => useSchedulerTaskGroupsMock(...args),
  useCreateSchedulerTaskGroup: () => ({
    isPending: false,
    mutateAsync: createMutateAsyncMock,
  }),
  useDeleteSchedulerTaskGroup: () => ({
    isPending: false,
    mutate: deleteMutateMock,
  }),
  usePauseSchedulerTaskGroup: () => ({
    isPending: false,
    mutate: pauseMutateMock,
  }),
  useResumeSchedulerTaskGroup: () => ({
    isPending: false,
    mutate: resumeMutateMock,
  }),
  useRunSchedulerTaskGroup: () => ({
    isPending: false,
    mutate: runMutateMock,
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
    createMutateAsyncMock.mockReset()
    deleteMutateMock.mockReset()
    pauseMutateMock.mockReset()
    resumeMutateMock.mockReset()
    runMutateMock.mockReset()
    useSchedulerTaskGroupsMock.mockReset()

    useSchedulerTaskGroupsMock.mockImplementation(() => ({
      data: {
        task_groups: [
          {
            id: 'group-1',
            name: 'nightly-check',
            project: 'synapse-network',
            cron_expr: '0 2 * * *',
            status: 'active',
            created_at: '2026-04-13T01:00:00+08:00',
            updated_at: '2026-04-13T01:00:00+08:00',
            last_run_at: '2026-04-13T02:00:00+08:00',
            next_run_at: '2026-04-14T02:00:00+08:00',
            last_result: 'fail',
            last_summary: 'docs:fail | profile:pass | plan:warn',
            latest_steps: [
              { id: 's1', batch_id: 'b1', task_group_id: 'group-1', check_type: 'docs', status: 'fail', duration_ms: 10, summary: 'docs failed', details: [], workflow_record_id: 'WF-1' },
              { id: 's2', batch_id: 'b1', task_group_id: 'group-1', check_type: 'profile', status: 'pass', duration_ms: 10, summary: 'profile passed', details: [], workflow_record_id: 'WF-2' },
              { id: 's3', batch_id: 'b1', task_group_id: 'group-1', check_type: 'plan', status: 'warn', duration_ms: 10, summary: 'plan warning', details: [], workflow_record_id: 'WF-3' },
            ],
            recent_results: ['fail', 'warn', 'pass'],
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    }))
  })

  it('renders task group cards with filters and cron help', async () => {
    renderPage()

    expect(screen.getByText('nightly-check')).toBeInTheDocument()
    expect(screen.getByText('最近结果: fail')).toBeInTheDocument()
    expect(screen.getByText('docs: fail')).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '+ 新增任务' }))

    expect(screen.getByTestId('create-task-group-form')).toBeInTheDocument()
    expect(screen.getByText('Cron 说明')).toBeInTheDocument()
    expect(screen.getByText('每小时的第 5 分钟执行一次')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '搜索' })).toBeInTheDocument()
  })

  it('submits task group creation and supports quick actions', async () => {
    createMutateAsyncMock.mockResolvedValue({ task_group: { id: 'group-2' } })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '+ 新增任务' }))
    await user.type(screen.getByPlaceholderText('nightly-check'), 'nightly-check')
    await user.selectOptions(screen.getByDisplayValue('synapse-network'), 'synapse-network-growing')
    await user.type(screen.getByPlaceholderText('0 2 * * *'), '0 2 * * *')
    await user.click(screen.getByRole('button', { name: '创建任务组' }))

    expect(createMutateAsyncMock).toHaveBeenCalledWith({
      name: 'nightly-check',
      project: 'synapse-network-growing',
      cron_expr: '0 2 * * *',
    })

    await user.click(screen.getByRole('button', { name: '立即执行' }))
    expect(runMutateMock).toHaveBeenCalledWith('group-1')

    await user.click(screen.getByRole('button', { name: '暂停' }))
    expect(pauseMutateMock).toHaveBeenCalledWith('group-1')
  })
})
