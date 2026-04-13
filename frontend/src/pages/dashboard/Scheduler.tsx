import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useCreateSchedulerTaskGroup,
  useDeleteSchedulerTaskGroup,
  usePauseSchedulerTaskGroup,
  useResumeSchedulerTaskGroup,
  useRunSchedulerTaskGroup,
  useSchedulerTaskGroups,
  type SchedulerTaskGroup,
} from '@/api/useScheduler'
import { useProjects } from '@/api/useProjects'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

interface CreateForm {
  name: string
  project: string
  cron_expr: string
}

interface FilterDraft {
  q: string
  project: string
  status: string
  last_result: string
  failed_only: boolean
}

const EMPTY_FORM: CreateForm = { name: '', project: '', cron_expr: '' }
const EMPTY_FILTERS: FilterDraft = { q: '', project: '', status: '', last_result: '', failed_only: false }
const CRON_EXAMPLES = [
  { expr: '5 * * * *', label: '每小时的第 5 分钟执行一次' },
  { expr: '0 * * * *', label: '每小时整点执行一次' },
  { expr: '0 2 * * *', label: '每天凌晨 2 点执行一次' },
  { expr: '30 9 * * 1-5', label: '工作日每天 09:30 执行一次' },
  { expr: '0 8 * * 1', label: '每周一早上 8 点执行一次' },
]

const RESULT_BADGE_CLASS: Record<string, string> = {
  pass: 'badge badge-green',
  warn: 'badge badge-yellow',
  fail: 'badge badge-red',
}

function ResultDot({ result }: { result: string }) {
  const color = result === 'fail' ? 'bg-rose-500' : result === 'warn' ? 'bg-amber-400' : 'bg-emerald-500'
  return <span className={`h-2.5 w-2.5 rounded-full ${color}`} aria-hidden="true" />
}

function LatestSteps({ taskGroup }: { taskGroup: SchedulerTaskGroup }) {
  if (!taskGroup.latest_steps.length) {
    return <span className="text-xs text-gray-400">暂无执行结果</span>
  }
  return (
    <div className="flex flex-wrap gap-2">
      {taskGroup.latest_steps.map(step => (
        <span key={step.id} className={RESULT_BADGE_CLASS[step.status] ?? 'badge badge-gray'}>
          {step.check_type}: {step.status}
        </span>
      ))}
    </div>
  )
}

export default function Scheduler() {
  const { data: projects } = useProjects()
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [formError, setFormError] = useState('')
  const [draftFilters, setDraftFilters] = useState<FilterDraft>(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState<FilterDraft>(EMPTY_FILTERS)
  const registeredProjects = projects?.projects ?? []

  const { data, isLoading, error } = useSchedulerTaskGroups(appliedFilters)
  const createTaskGroup = useCreateSchedulerTaskGroup()
  const deleteTaskGroup = useDeleteSchedulerTaskGroup()
  const pauseTaskGroup = usePauseSchedulerTaskGroup()
  const resumeTaskGroup = useResumeSchedulerTaskGroup()
  const runTaskGroup = useRunSchedulerTaskGroup()

  useEffect(() => {
    if (form.project || registeredProjects.length === 0) return
    setForm(current => ({ ...current, project: registeredProjects[0]?.id ?? '' }))
  }, [form.project, registeredProjects])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.name.trim() || !form.project.trim() || !form.cron_expr.trim()) {
      setFormError('项目、任务名称、Cron 表达式为必填')
      return
    }
    try {
      await createTaskGroup.mutateAsync(form)
      setForm({ ...EMPTY_FORM, project: registeredProjects[0]?.id ?? '' })
      setShowForm(false)
    } catch {
      setFormError('创建失败，请检查字段')
    }
  }

  const applyFilters = (e: React.FormEvent) => {
    e.preventDefault()
    setAppliedFilters(draftFilters)
  }

  if (isLoading) return <LoadingSpinner text="加载调度任务组..." />

  return (
    <div className="space-y-6" data-testid="scheduler-page">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title">调度器</h1>
          <p className="mt-1 text-sm text-gray-500">
            Scheduler 用来给已接入项目定时跑治理检查。现在默认按任务组管理，一个任务组会执行 `docs`、`profile`、`plan` 三个检查。
          </p>
        </div>
        <button className="btn btn-primary text-sm" onClick={() => setShowForm(v => !v)}>
          {showForm ? '× 取消' : '+ 新增任务'}
        </button>
      </div>

      {error && <ErrorAlert message="调度任务组加载失败" />}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl border border-gray-100 p-5 space-y-4" data-testid="create-task-group-form">
          <h2 className="section-title">新增调度任务组</h2>
          {formError && <p className="text-sm text-red-500">{formError}</p>}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">任务组名称</label>
              <input
                className="input w-full"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="nightly-check"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">项目</label>
              <select
                className="input w-full"
                value={form.project}
                onChange={e => setForm(f => ({ ...f, project: e.target.value }))}
              >
                {registeredProjects.length === 0 ? (
                  <option value="">暂无已注册项目</option>
                ) : (
                  registeredProjects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.id}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">固定子检查</label>
              <div className="flex h-11 flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-slate-50 px-3 text-sm text-slate-600">
                <span className="badge badge-blue">docs</span>
                <span className="badge badge-blue">profile</span>
                <span className="badge badge-blue">plan</span>
              </div>
            </div>
            <div className="lg:col-span-3">
              <label className="block text-xs text-gray-500 mb-1">Cron 表达式</label>
              <input
                className="input w-full font-mono"
                value={form.cron_expr}
                onChange={e => setForm(f => ({ ...f, cron_expr: e.target.value }))}
                placeholder="0 2 * * *"
              />
              <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <p className="font-medium text-slate-700">Cron 说明</p>
                <p className="mt-1 font-mono text-xs text-slate-500">分钟 小时 日 月 星期</p>
                <div className="mt-2 space-y-1">
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
            </div>
          </div>

          <button type="submit" className="btn btn-primary" disabled={createTaskGroup.isPending || registeredProjects.length === 0}>
            {createTaskGroup.isPending ? '创建中...' : '创建任务组'}
          </button>
        </form>
      )}

      <form onSubmit={applyFilters} className="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="section-title">筛选任务组</h2>
          <button
            type="button"
            className="text-xs text-slate-500 hover:text-slate-700"
            onClick={() => {
              setDraftFilters(EMPTY_FILTERS)
              setAppliedFilters(EMPTY_FILTERS)
            }}
          >
            清空筛选
          </button>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          <input
            className="input w-full"
            placeholder="搜索任务组名称 / cron / 项目"
            value={draftFilters.q}
            onChange={e => setDraftFilters(current => ({ ...current, q: e.target.value }))}
          />
          <select
            className="input w-full"
            value={draftFilters.project}
            onChange={e => setDraftFilters(current => ({ ...current, project: e.target.value }))}
          >
            <option value="">全部项目</option>
            {registeredProjects.map(project => (
              <option key={project.id} value={project.id}>
                {project.id}
              </option>
            ))}
          </select>
          <select
            className="input w-full"
            value={draftFilters.status}
            onChange={e => setDraftFilters(current => ({ ...current, status: e.target.value }))}
          >
            <option value="">全部状态</option>
            <option value="active">已启用</option>
            <option value="paused">已暂停</option>
          </select>
          <select
            className="input w-full"
            value={draftFilters.last_result}
            onChange={e => setDraftFilters(current => ({ ...current, last_result: e.target.value }))}
          >
            <option value="">全部结果</option>
            <option value="pass">pass</option>
            <option value="warn">warn</option>
            <option value="fail">fail</option>
          </select>
          <button type="submit" className="btn btn-primary">搜索</button>
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={draftFilters.failed_only}
            onChange={e => setDraftFilters(current => ({ ...current, failed_only: e.target.checked }))}
          />
          仅看失败/告警任务
        </label>
      </form>

      {(!data?.task_groups || data.task_groups.length === 0) ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <div className="text-4xl mb-3">⏰</div>
          <p className="text-gray-500">暂无调度任务组</p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.task_groups.map(taskGroup => (
            <div key={taskGroup.id} className="bg-white rounded-xl border border-gray-100 p-5 space-y-4" data-testid="task-group-item">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-3 flex-wrap">
                    <p className="font-semibold text-gray-800">{taskGroup.name}</p>
                    <span className={taskGroup.status === 'active' ? 'badge badge-green' : 'badge badge-gray'}>
                      {taskGroup.status === 'active' ? '已启用' : '已暂停'}
                    </span>
                    {taskGroup.last_result && (
                      <span className={RESULT_BADGE_CLASS[taskGroup.last_result] ?? 'badge badge-gray'}>
                        最近结果: {taskGroup.last_result}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-mono text-gray-500">{taskGroup.cron_expr} · {taskGroup.project}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400 flex-wrap">
                    {taskGroup.last_run_at && <span>上次运行: {formatDate(taskGroup.last_run_at)}</span>}
                    {taskGroup.next_run_at && <span>下次运行: {formatDate(taskGroup.next_run_at)}</span>}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap justify-end">
                  <button
                    className="btn btn-outline text-xs"
                    onClick={() => runTaskGroup.mutate(taskGroup.id)}
                    disabled={runTaskGroup.isPending}
                  >
                    立即执行
                  </button>
                  {taskGroup.status === 'active' ? (
                    <button
                      className="btn btn-outline text-xs"
                      onClick={() => pauseTaskGroup.mutate(taskGroup.id)}
                      disabled={pauseTaskGroup.isPending}
                    >
                      暂停
                    </button>
                  ) : (
                    <button
                      className="btn btn-outline text-xs"
                      onClick={() => resumeTaskGroup.mutate(taskGroup.id)}
                      disabled={resumeTaskGroup.isPending}
                    >
                      启动
                    </button>
                  )}
                  <Link className="btn btn-outline text-xs" to={`/scheduler/${taskGroup.id}`}>
                    查看详情
                  </Link>
                  <button
                    className="text-xs text-red-400 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50"
                    onClick={() => {
                      if (window.confirm(`确认删除任务组 "${taskGroup.name}" 吗？`)) {
                        deleteTaskGroup.mutate(taskGroup.id)
                      }
                    }}
                    disabled={deleteTaskGroup.isPending}
                  >
                    删除
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-500">最近结果</span>
                {taskGroup.recent_results.length === 0 ? (
                  <span className="text-xs text-gray-400">暂无执行历史</span>
                ) : (
                  taskGroup.recent_results.map((result, index) => <ResultDot key={`${taskGroup.id}-${result}-${index}`} result={result} />)
                )}
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-2">最近一次子检查摘要</p>
                <LatestSteps taskGroup={taskGroup} />
              </div>

              {taskGroup.last_summary && (
                <div className="rounded-xl bg-slate-50 px-4 py-3 text-xs text-slate-600">
                  {taskGroup.last_summary}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
