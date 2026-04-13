import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import SchedulerDetail from '@/pages/dashboard/SchedulerDetail'

const updateMutateAsyncMock = vi.fn()
const pauseMutateMock = vi.fn()
const resumeMutateMock = vi.fn()
const runMutateMock = vi.fn()
const deleteMutateAsyncMock = vi.fn()
const useSchedulerTaskGroupRunsMock = vi.fn()
const useSchedulerTaskGroupMock = vi.fn()

vi.mock('@/api/useScheduler', () => ({
  useSchedulerTaskGroup: (...args: unknown[]) => useSchedulerTaskGroupMock(...args),
  useSchedulerTaskGroupRuns: (...args: unknown[]) => useSchedulerTaskGroupRunsMock(...args),
  useUpdateSchedulerTaskGroup: () => ({
    isPending: false,
    mutateAsync: updateMutateAsyncMock,
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
  useDeleteSchedulerTaskGroup: () => ({
    isPending: false,
    mutateAsync: deleteMutateAsyncMock,
  }),
}))

vi.mock('@/api/useProjects', () => ({
  useProjects: () => ({
    data: {
      projects: [
        { id: 'synapse-network', name: 'synapse-network' },
        { id: 'agents-memory', name: 'agents-memory' },
      ],
    },
  }),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/scheduler/group-1']}>
      <Routes>
        <Route path="/scheduler/:id" element={<SchedulerDetail />} />
        <Route path="/scheduler" element={<div>scheduler list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Scheduler detail page', () => {
  beforeEach(() => {
    useSchedulerTaskGroupMock.mockReset()
    updateMutateAsyncMock.mockReset()
    pauseMutateMock.mockReset()
    resumeMutateMock.mockReset()
    runMutateMock.mockReset()
    deleteMutateAsyncMock.mockReset()
    useSchedulerTaskGroupRunsMock.mockReset()
    useSchedulerTaskGroupMock.mockReturnValue({
      data: {
        task_group: {
          id: 'group-1',
          name: 'nightly-check',
          project: 'synapse-network',
          cron_expr: '0 2 * * *',
          status: 'active',
          created_at: '2026-04-13T01:00:00+08:00',
          updated_at: '2026-04-13T01:00:00+08:00',
          last_run_at: '2026-04-13T02:00:00+08:00',
          next_run_at: '2026-04-14T02:00:00+08:00',
          last_result: 'warn',
          last_summary: 'docs:pass | profile:warn | plan:pass',
          latest_steps: [
            {
              id: 'step-1',
              batch_id: 'batch-1',
              task_group_id: 'group-1',
              check_type: 'docs',
              status: 'pass',
              duration_ms: 12,
              summary: 'docs ok',
              details: [],
              workflow_record_id: 'WF-1',
            },
          ],
          recent_results: ['warn', 'pass'],
        },
        latest_batch: null,
      },
      isLoading: false,
      error: null,
    })
    useSchedulerTaskGroupRunsMock.mockImplementation((_id: string, params?: { page?: number; pageSize?: number }) => {
      const page = params?.page ?? 1
      if (page === 2) {
        return {
          data: {
            runs: [
              {
                id: 'batch-2',
                task_group_id: 'group-1',
                task_group_name: 'nightly-check',
                project: 'synapse-network',
                run_at: '2026-04-12T02:00:00+08:00',
                finished_at: '2026-04-12T02:00:05+08:00',
                overall_status: 'pass',
                duration_ms: 4500,
                trigger: 'manual',
                steps: [
                  {
                    id: 'step-4',
                    batch_id: 'batch-2',
                    task_group_id: 'group-1',
                    check_type: 'docs',
                    status: 'pass',
                    duration_ms: 20,
                    summary: 'docs ok',
                    details: [],
                    workflow_record_id: 'WF-4',
                  },
                ],
              },
            ],
            total: 2,
            page: 2,
            page_size: 1,
            total_pages: 2,
          },
          isLoading: false,
          error: null,
        }
      }
      return {
        data: {
          runs: [
            {
              id: 'batch-1',
              task_group_id: 'group-1',
              task_group_name: 'nightly-check',
              project: 'synapse-network',
              run_at: '2026-04-13T02:00:00+08:00',
              finished_at: '2026-04-13T02:00:05+08:00',
              overall_status: 'warn',
              duration_ms: 5000,
              trigger: 'scheduled',
              steps: [
                {
                  id: 'step-1',
                  batch_id: 'batch-1',
                  task_group_id: 'group-1',
                  check_type: 'docs',
                  status: 'pass',
                  duration_ms: 20,
                  summary: 'docs ok',
                  details: ['[PASS] docs_entrypoint'],
                  workflow_record_id: 'WF-1',
                },
                {
                  id: 'step-2',
                  batch_id: 'batch-1',
                  task_group_id: 'group-1',
                  check_type: 'profile',
                  status: 'warn',
                  duration_ms: 30,
                  summary: 'profile warning',
                  details: ['[WARN] tests missing'],
                  workflow_record_id: 'WF-2',
                },
                {
                  id: 'step-3',
                  batch_id: 'batch-1',
                  task_group_id: 'group-1',
                  check_type: 'plan',
                  status: 'pass',
                  duration_ms: 40,
                  summary: 'plan ok',
                  details: [],
                  workflow_record_id: 'WF-3',
                },
              ],
            },
          ],
          total: 2,
          page: 1,
          page_size: 1,
          total_pages: 2,
        },
        isLoading: false,
        error: null,
      }
    })
  })

  it('renders task group summary and run history details', () => {
    renderPage()

    expect(screen.getByText('nightly-check')).toBeInTheDocument()
    expect(screen.getByText('最近 2 次')).toBeInTheDocument()
    expect(screen.getByText('Cron 常用配置')).toBeInTheDocument()
    expect(screen.getByTestId('scheduler-runs-pagination-summary')).toHaveTextContent('第 1 / 2 页，每页 1 条')
    expect(screen.getByText('运行于 2026/04/13 · 总耗时 5000ms')).toBeInTheDocument()

    expect(screen.getByText('docs-check')).toBeInTheDocument()
    expect(screen.getByText('[WARN] tests missing')).toBeInTheDocument()
    expect(screen.getAllByText('查看 workflow').length).toBeGreaterThan(0)
    expect(screen.getAllByText('查看 checks').length).toBeGreaterThan(0)
  })

  it('supports editing and quick actions', async () => {
    updateMutateAsyncMock.mockResolvedValue({ task_group: { id: 'group-1' } })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '编辑' }))

    const nameInput = screen.getByDisplayValue('nightly-check')
    await user.clear(nameInput)
    await user.type(nameInput, 'nightly-check-updated')

    await user.selectOptions(screen.getByDisplayValue('synapse-network'), 'agents-memory')

    const cronInput = screen.getByDisplayValue('0 2 * * *')
    await user.clear(cronInput)
    await user.type(cronInput, '5 * * * *')

    await user.selectOptions(screen.getByDisplayValue('已启用'), 'paused')
    await user.click(screen.getByRole('button', { name: '保存修改' }))

    expect(updateMutateAsyncMock).toHaveBeenCalledWith({
      id: 'group-1',
      name: 'nightly-check-updated',
      project: 'agents-memory',
      cron_expr: '5 * * * *',
      status: 'paused',
    })

    await user.click(screen.getByRole('button', { name: '立即执行' }))
    expect(runMutateMock).toHaveBeenCalledWith('group-1')

    await user.click(screen.getByRole('button', { name: '暂停' }))
    expect(pauseMutateMock).toHaveBeenCalledWith('group-1')
  })

  it('moves run history to the next page', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '下一页' }))

    expect(screen.getByText('运行于 2026/04/12 · 总耗时 4500ms')).toBeInTheDocument()
    expect(screen.getByTestId('scheduler-runs-pagination-summary')).toHaveTextContent('第 2 / 2 页，每页 1 条')
  })

  it('does not crash when task detail transitions from loading to loaded', async () => {
    useSchedulerTaskGroupMock
      .mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        error: null,
      })
      .mockReturnValue({
        data: {
          task_group: {
            id: 'group-1',
            name: 'nightly-check',
            project: 'synapse-network',
            cron_expr: '0 2 * * *',
            status: 'active',
            created_at: '2026-04-13T01:00:00+08:00',
            updated_at: '2026-04-13T01:00:00+08:00',
            last_run_at: '2026-04-13T02:00:00+08:00',
            next_run_at: '2026-04-14T02:00:00+08:00',
            last_result: 'warn',
            last_summary: 'docs:pass | profile:warn | plan:pass',
            latest_steps: [],
            recent_results: ['warn', 'pass'],
          },
          latest_batch: null,
        },
        isLoading: false,
        error: null,
      })

    const { rerender } = render(
      <MemoryRouter initialEntries={['/scheduler/group-1']}>
        <Routes>
          <Route path="/scheduler/:id" element={<SchedulerDetail />} />
          <Route path="/scheduler" element={<div>scheduler list</div>} />
        </Routes>
      </MemoryRouter>,
    )

    rerender(
      <MemoryRouter initialEntries={['/scheduler/group-1']}>
        <Routes>
          <Route path="/scheduler/:id" element={<SchedulerDetail />} />
          <Route path="/scheduler" element={<div>scheduler list</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('nightly-check')).toBeInTheDocument()
  })
})
