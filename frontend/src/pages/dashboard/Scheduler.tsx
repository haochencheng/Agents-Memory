import { useState } from 'react'
import { useSchedulerTasks, useCreateSchedulerTask, useDeleteSchedulerTask } from '@/api/useScheduler'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

interface CreateForm {
  name: string
  check_type: 'docs' | 'profile' | 'plan'
  project: string
  cron_expr: string
}

const EMPTY_FORM: CreateForm = { name: '', check_type: 'docs', project: '', cron_expr: '' }

export default function Scheduler() {
  const { data: tasks, isLoading, error } = useSchedulerTasks()
  const createTask = useCreateSchedulerTask()
  const deleteTask = useDeleteSchedulerTask()
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [formError, setFormError] = useState('')

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.name.trim() || !form.project.trim() || !form.cron_expr.trim()) {
      setFormError('项目、任务名称、Cron 表达式为必填')
      return
    }
    try {
      await createTask.mutateAsync(form)
      setForm(EMPTY_FORM)
      setShowForm(false)
    } catch {
      setFormError('创建失败，请检查字段')
    }
  }

  if (isLoading) return <LoadingSpinner text="加载调度任务..." />
  if (error) return <ErrorAlert message="调度任务加载失败" />

  return (
    <div className="space-y-6" data-testid="scheduler-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">调度器</h1>
        <button
          className="btn btn-primary text-sm"
          onClick={() => setShowForm(v => !v)}
        >
          {showForm ? '× 取消' : '+ 新增任务'}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white rounded-xl border border-gray-100 p-5 space-y-4"
          data-testid="create-task-form"
        >
          <h2 className="section-title">新增调度任务</h2>
          {formError && <p className="text-sm text-red-500">{formError}</p>}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
              <input
                className="input w-full"
                value={form.project}
                onChange={e => setForm(f => ({ ...f, project: e.target.value }))}
                placeholder="my-project"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Check 类型</label>
              <select
                className="input w-full"
                value={form.check_type}
                onChange={e => setForm(f => ({ ...f, check_type: e.target.value as 'docs' | 'profile' | 'plan' }))}
              >
                <option value="docs">docs</option>
                <option value="profile">profile</option>
                <option value="plan">plan</option>
              </select>
            </div>
            <div>
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
            disabled={createTask.isPending}
          >
            {createTask.isPending ? '创建中...' : '创建任务'}
          </button>
        </form>
      )}

      {/* Task list */}
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
                  <p className="text-xs text-gray-400 mt-0.5">上次运行: {formatDate(t.last_run)}</p>
                )}
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
