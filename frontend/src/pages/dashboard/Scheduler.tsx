import { useEffect, useState } from 'react'
import { useSchedulerTasks, useCreateSchedulerTask, useDeleteSchedulerTask } from '@/api/useScheduler'
import { useProjects } from '@/api/useProjects'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

interface CreateForm {
  name: string
  project: string
  cron_expr: string
}

const EMPTY_FORM: CreateForm = { name: '', project: '', cron_expr: '' }

export default function Scheduler() {
  const { data: tasks, isLoading, error } = useSchedulerTasks()
  const { data: projects } = useProjects()
  const createTask = useCreateSchedulerTask()
  const deleteTask = useDeleteSchedulerTask()
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [formError, setFormError] = useState('')
  const registeredProjects = projects?.projects ?? []

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
      await createTask.mutateAsync(form)
      setForm({
        ...EMPTY_FORM,
        project: registeredProjects[0]?.id ?? '',
      })
      setShowForm(false)
    } catch {
      setFormError('创建失败，请检查字段')
    }
  }

  if (isLoading) return <LoadingSpinner text="加载调度任务..." />

  return (
    <div className="space-y-6" data-testid="scheduler-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">调度器</h1>
          <p className="mt-1 text-sm text-gray-500">
            Scheduler 用来给已接入项目定时跑治理检查。任务会持久化到磁盘、服务启动后自动恢复，并按计划执行 `docs`、`profile`、`plan` 三个检查。
          </p>
        </div>
        <button
          className="btn btn-primary text-sm"
          onClick={() => setShowForm(v => !v)}
        >
          {showForm ? '× 取消' : '+ 新增任务'}
        </button>
      </div>

      {error && <ErrorAlert message="调度任务加载失败" />}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white rounded-xl border border-gray-100 p-5 space-y-4"
          data-testid="create-task-form"
        >
          <h2 className="section-title">新增调度任务</h2>
          {formError && <p className="text-sm text-red-500">{formError}</p>}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">任务名称</label>
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
              <label className="block text-xs text-gray-500 mb-1">将创建的检查任务</label>
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
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={createTask.isPending || registeredProjects.length === 0}
          >
            {createTask.isPending ? '创建中...' : '创建 3 个检查任务'}
          </button>
        </form>
      )}

      {showForm && registeredProjects.length === 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          当前没有已注册项目。请先完成项目接入，再创建调度检查任务。
        </div>
      )}

      {(!tasks?.tasks || tasks.tasks.length === 0) ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <div className="text-4xl mb-3">⏰</div>
          <p className="text-gray-500">暂无调度任务</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.tasks.map(t => (
            <div
              key={t.id}
              className="bg-white rounded-xl border border-gray-100 p-4 flex items-center gap-4"
              data-testid="task-item"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800">{t.name}</p>
                <p className="text-sm font-mono text-gray-500">{t.cron_expr} — {t.check_type} · {t.project}</p>
                {t.last_run && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    上次运行: {formatDate(t.last_run)}
                    {t.last_summary ? ` · ${t.last_summary}` : ''}
                  </p>
                )}
                {t.next_run && <p className="text-xs text-gray-400 mt-0.5">下次运行: {formatDate(t.next_run)}</p>}
              </div>
              <span className={`badge ${t.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                {t.status === 'active' ? '已启用' : '已暂停'}
              </span>
              <button
                className="text-xs text-red-400 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50"
                onClick={() => deleteTask.mutate(t.id)}
                disabled={deleteTask.isPending}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
