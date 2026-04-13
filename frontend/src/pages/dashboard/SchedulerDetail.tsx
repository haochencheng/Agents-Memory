import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useProjects } from '@/api/useProjects'
import {
  useDeleteSchedulerTaskGroup,
  usePauseSchedulerTaskGroup,
  useResumeSchedulerTaskGroup,
  useRunSchedulerTaskGroup,
  useSchedulerTaskGroup,
  useSchedulerTaskGroupRuns,
  useUpdateSchedulerTaskGroup,
} from '@/api/useScheduler'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate, formatDateTime } from '@/lib/utils'

interface EditForm {
  name: string
  project: string
  cron_expr: string
  status: 'active' | 'paused'
}

const RESULT_BADGE_CLASS: Record<string, string> = {
  pass: 'badge badge-green',
  warn: 'badge badge-yellow',
  fail: 'badge badge-red',
}

const RUN_PAGE_SIZE = 10
const CRON_EXAMPLES = [
  { expr: '5 * * * *', label: '每小时的第 5 分钟执行一次' },
  { expr: '0 * * * *', label: '每小时整点执行一次' },
  { expr: '0 2 * * *', label: '每天凌晨 2 点执行一次' },
  { expr: '30 9 * * 1-5', label: '工作日每天 09:30 执行一次' },
  { expr: '0 8 * * 1', label: '每周一早上 8 点执行一次' },
]

function buildPageNumbers(currentPage: number, totalPages: number): number[] {
  const start = Math.max(1, currentPage - 2)
  const end = Math.min(totalPages, currentPage + 2)
  const pages: number[] = []
  for (let page = start; page <= end; page += 1) {
    pages.push(page)
  }
  return pages
}

export default function SchedulerDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialRunsPage = Number.parseInt(searchParams.get('runsPage') ?? '1', 10)
  const [runsPage, setRunsPage] = useState(Number.isFinite(initialRunsPage) && initialRunsPage > 0 ? initialRunsPage : 1)
  const { data, isLoading, error } = useSchedulerTaskGroup(id)
  const { data: runsData, isLoading: runsLoading, error: runsError } = useSchedulerTaskGroupRuns(id, { page: runsPage, pageSize: RUN_PAGE_SIZE })
  const { data: projects } = useProjects()
  const updateTaskGroup = useUpdateSchedulerTaskGroup()
  const pauseTaskGroup = usePauseSchedulerTaskGroup()
  const resumeTaskGroup = useResumeSchedulerTaskGroup()
  const runTaskGroup = useRunSchedulerTaskGroup()
  const deleteTaskGroup = useDeleteSchedulerTaskGroup()
  const [editing, setEditing] = useState(false)
  const [formError, setFormError] = useState('')
  const [form, setForm] = useState<EditForm>({
    name: '',
    project: '',
    cron_expr: '',
    status: 'active',
  })
  const taskGroup = data?.task_group

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams)
    if (runsPage > 1) {
      nextParams.set('runsPage', String(runsPage))
    } else {
      nextParams.delete('runsPage')
    }
    setSearchParams(nextParams, { replace: true })
  }, [runsPage, searchParams, setSearchParams])

  useEffect(() => {
    if (!taskGroup) return
    setForm(current => {
      const next = {
        name: taskGroup.name,
        project: taskGroup.project,
        cron_expr: taskGroup.cron_expr,
        status: taskGroup.status,
      }
      if (
        current.name === next.name &&
        current.project === next.project &&
        current.cron_expr === next.cron_expr &&
        current.status === next.status
      ) {
        return current
      }
      return next
    })
  }, [taskGroup?.id, taskGroup?.name, taskGroup?.project, taskGroup?.cron_expr, taskGroup?.status])

  const resolvedTaskGroup = data?.task_group
  const runs = runsData?.runs ?? []
  const registeredProjects = projects?.projects ?? []
  const runPageNumbers = buildPageNumbers(runsData?.page ?? runsPage, runsData?.total_pages ?? 1)

  if (isLoading) return <LoadingSpinner text={`加载调度任务组 ${id}...`} />
  if (error || !resolvedTaskGroup) return <ErrorAlert message={`调度任务组 "${id}" 加载失败`} />

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.name.trim() || !form.project.trim() || !form.cron_expr.trim()) {
      setFormError('任务组名称、项目、Cron 表达式为必填')
      return
    }
    try {
      await updateTaskGroup.mutateAsync({
        id,
        name: form.name,
        project: form.project,
        cron_expr: form.cron_expr,
        status: form.status,
      })
      setEditing(false)
    } catch {
      setFormError('保存失败，请检查字段')
    }
  }

  return (
    <div className="space-y-6" data-testid="scheduler-detail-page">
      <div className="flex items-center gap-3">
        <Link to="/scheduler" className="text-sm text-blue-500 hover:underline">← 返回调度器</Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{resolvedTaskGroup.name}</h1>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            <span className="rounded-full bg-slate-100 px-3 py-1.5">项目: {resolvedTaskGroup.project}</span>
            <span className="rounded-full bg-slate-100 px-3 py-1.5">Cron: {resolvedTaskGroup.cron_expr}</span>
            <span className="rounded-full bg-slate-100 px-3 py-1.5">状态: {resolvedTaskGroup.status}</span>
            {resolvedTaskGroup.last_result && (
              <span className={`rounded-full px-3 py-1.5 ${RESULT_BADGE_CLASS[resolvedTaskGroup.last_result] ?? 'badge badge-gray'}`}>
                最近结果: {resolvedTaskGroup.last_result}
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button className="btn btn-outline text-sm" onClick={() => setEditing(v => !v)}>
            {editing ? '取消编辑' : '编辑'}
          </button>
          <button className="btn btn-outline text-sm" onClick={() => runTaskGroup.mutate(id)} disabled={runTaskGroup.isPending}>
            立即执行
          </button>
          {resolvedTaskGroup.status === 'active' ? (
            <button className="btn btn-outline text-sm" onClick={() => pauseTaskGroup.mutate(id)} disabled={pauseTaskGroup.isPending}>
              暂停
            </button>
          ) : (
            <button className="btn btn-outline text-sm" onClick={() => resumeTaskGroup.mutate(id)} disabled={resumeTaskGroup.isPending}>
              启动
            </button>
          )}
          <button
            className="text-sm text-red-500 hover:text-red-700"
            onClick={async () => {
              if (!window.confirm(`确认删除任务组 "${resolvedTaskGroup.name}" 吗？`)) return
              await deleteTaskGroup.mutateAsync(id)
              navigate('/scheduler')
            }}
            disabled={deleteTaskGroup.isPending}
          >
            删除
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-slate-500">上次运行</p>
          <p className="mt-2 text-sm text-slate-700">{resolvedTaskGroup.last_run_at ? formatDateTime(resolvedTaskGroup.last_run_at) : '暂无'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-slate-500">下次运行</p>
          <p className="mt-2 text-sm text-slate-700">{resolvedTaskGroup.next_run_at ? formatDateTime(resolvedTaskGroup.next_run_at) : '已暂停'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-slate-500">最近摘要</p>
          <p className="mt-2 text-sm text-slate-700">{resolvedTaskGroup.last_summary || '暂无'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-slate-500">执行历史</p>
          <p className="mt-2 text-sm text-slate-700">最近 {runsData?.total ?? 0} 次</p>
          <p className="mt-1 text-xs text-slate-400">
            第 {runsData?.page ?? 1} / {(runsData?.total_pages ?? 0) || 1} 页
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        <p className="font-medium text-slate-700">Cron 常用配置</p>
        <p className="mt-1 font-mono text-xs text-slate-500">分钟 小时 日 月 星期</p>
        <div className="mt-2 grid gap-1 md:grid-cols-2">
          {CRON_EXAMPLES.map(item => (
            <p key={item.expr}>
              <span className="font-mono text-slate-700">{item.expr}</span>
              <span className="ml-2">{item.label}</span>
            </p>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          支持 `*`、范围 `1-5`、列表 `1,3,5`、步进 `*/2` 这种标准 5 段写法。
        </p>
      </div>

      {editing && (
        <form onSubmit={handleSave} className="bg-white rounded-xl border border-gray-100 p-5 space-y-4" data-testid="scheduler-edit-form">
          <h2 className="section-title">编辑任务组</h2>
          {formError && <p className="text-sm text-red-500">{formError}</p>}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">任务组名称</label>
              <input className="input w-full" value={form.name} onChange={e => setForm(current => ({ ...current, name: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">项目</label>
              <select className="input w-full" value={form.project} onChange={e => setForm(current => ({ ...current, project: e.target.value }))}>
                {registeredProjects.map(project => (
                  <option key={project.id} value={project.id}>
                    {project.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Cron 表达式</label>
              <input className="input w-full font-mono" value={form.cron_expr} onChange={e => setForm(current => ({ ...current, cron_expr: e.target.value }))} />
              <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <p className="font-medium text-slate-700">Cron 常用配置</p>
                <div className="mt-2 space-y-1">
                  {CRON_EXAMPLES.map(item => (
                    <p key={item.expr}>
                      <span className="font-mono text-slate-700">{item.expr}</span>
                      <span className="ml-2">{item.label}</span>
                    </p>
                  ))}
                </div>
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">状态</label>
              <select className="input w-full" value={form.status} onChange={e => setForm(current => ({ ...current, status: e.target.value as 'active' | 'paused' }))}>
                <option value="active">已启用</option>
                <option value="paused">已暂停</option>
              </select>
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={updateTaskGroup.isPending}>
            {updateTaskGroup.isPending ? '保存中...' : '保存修改'}
          </button>
        </form>
      )}

      <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="section-title">执行历史</h2>
          {runsLoading && <span className="text-xs text-slate-400">加载中...</span>}
        </div>
        {runsError && <ErrorAlert message="调度执行历史加载失败" />}
        {!runsLoading && !runsError && (
          <div className="flex flex-col gap-2 rounded-xl border border-gray-100 bg-slate-50 px-4 py-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <span>按批次展示最近 200 次中的当前分页结果</span>
            <span data-testid="scheduler-runs-pagination-summary">
              第 {runsData?.page ?? 1} / {(runsData?.total_pages ?? 0) || 1} 页，每页 {runsData?.page_size ?? RUN_PAGE_SIZE} 条
            </span>
          </div>
        )}
        {!runsLoading && runs.length === 0 && <div className="text-sm text-gray-400">暂无执行历史</div>}
        <div className="space-y-3">
          {runs.map(run => (
            <details key={run.id} className="rounded-xl border border-gray-100 bg-slate-50 p-4" data-testid="scheduler-run-item">
              <summary className="cursor-pointer list-none">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={RESULT_BADGE_CLASS[run.overall_status] ?? 'badge badge-gray'}>{run.overall_status}</span>
                      <span className="text-sm font-medium text-slate-700">{run.trigger === 'manual' ? '手动执行' : '定时执行'}</span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      运行于 {formatDate(run.run_at)} · 总耗时 {run.duration_ms}ms
                    </p>
                  </div>
                  <div className="flex gap-2 flex-wrap justify-end">
                    {run.steps.map(step => (
                      <span key={step.id} className={RESULT_BADGE_CLASS[step.status] ?? 'badge badge-gray'}>
                        {step.check_type}: {step.status}
                      </span>
                    ))}
                  </div>
                </div>
              </summary>

              <div className="mt-4 space-y-3">
                {run.steps.map(step => (
                  <div key={step.id} className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className={RESULT_BADGE_CLASS[step.status] ?? 'badge badge-gray'}>{step.status}</span>
                        <span className="font-medium text-slate-700">{step.check_type}-check</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        <span>{step.duration_ms}ms</span>
                        <Link to="/checks" className="text-blue-500 hover:underline">
                          查看 checks
                        </Link>
                        {step.workflow_record_id && (
                          <Link to={`/workflow/${step.workflow_record_id}`} className="text-blue-500 hover:underline">
                            查看 workflow
                          </Link>
                        )}
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{step.summary}</p>
                    {step.details.length > 0 && (
                      <ul className="mt-3 space-y-1 text-xs text-slate-500">
                        {step.details.map(detail => (
                          <li key={detail}>{detail}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
        {(runsData?.total_pages ?? 0) > 1 && (
          <div className="flex items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3">
            <button
              type="button"
              className="btn btn-outline"
              disabled={(runsData?.page ?? 1) <= 1}
              onClick={() => setRunsPage(current => Math.max(1, current - 1))}
            >
              上一页
            </button>

            <div className="flex items-center gap-2 text-sm text-gray-500" data-testid="scheduler-runs-pagination-controls">
              {runPageNumbers[0] > 1 && (
                <>
                  <button type="button" className="btn btn-outline" onClick={() => setRunsPage(1)}>
                    1
                  </button>
                  {runPageNumbers[0] > 2 && <span>…</span>}
                </>
              )}

              {runPageNumbers.map(pageNumber => (
                <button
                  key={pageNumber}
                  type="button"
                  className={pageNumber === (runsData?.page ?? runsPage) ? 'btn' : 'btn btn-outline'}
                  onClick={() => setRunsPage(pageNumber)}
                >
                  {pageNumber}
                </button>
              ))}

              {(runPageNumbers[runPageNumbers.length - 1] ?? 1) < (runsData?.total_pages ?? 1) && (
                <>
                  {(runPageNumbers[runPageNumbers.length - 1] ?? 1) < (runsData?.total_pages ?? 1) - 1 && <span>…</span>}
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => setRunsPage(runsData?.total_pages ?? 1)}
                  >
                    {runsData?.total_pages ?? 1}
                  </button>
                </>
              )}
            </div>

            <button
              type="button"
              className="btn btn-outline"
              disabled={(runsData?.page ?? 1) >= (runsData?.total_pages ?? 1)}
              onClick={() => setRunsPage(current => Math.min(runsData?.total_pages ?? current, current + 1))}
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
