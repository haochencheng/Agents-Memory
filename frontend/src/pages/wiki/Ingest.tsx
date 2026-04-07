import { useState } from 'react'
import { useIngest } from '@/api/useScheduler'

interface IngestForm {
  project: string
  source_type: string
  content: string
}

const EMPTY_FORM: IngestForm = { project: '', source_type: 'markdown', content: '' }

export default function Ingest() {
  const ingest = useIngest()
  const [form, setForm] = useState<IngestForm>(EMPTY_FORM)
  const [log, setLog] = useState<string[]>([])
  const [formError, setFormError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.project.trim()) {
      setFormError('项目名称为必填')
      return
    }
    setLog(prev => [...prev, `[${new Date().toISOString()}] 启动摄入: project=${form.project}`])
    try {
      const result = await ingest.mutateAsync({
        project: form.project,
        source_type: form.source_type,
        content: form.content,
      })
      const msg = typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result)
      setLog(prev => [...prev, `[OK] ${msg}`])
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setLog(prev => [...prev, `[ERR] ${msg}`])
      setFormError('摄入失败: ' + msg)
    }
  }

  return (
    <div className="space-y-6" data-testid="ingest-page">
      <h1 className="page-title">知识摄入</h1>

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-xl border border-gray-100 p-5 space-y-4"
        data-testid="ingest-form"
      >
        <h2 className="section-title">摄入配置</h2>

        {formError && (
          <p className="text-sm text-red-500 bg-red-50 rounded px-3 py-2">{formError}</p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">项目名称 *</label>
            <input
              className="input w-full"
              value={form.project}
              onChange={e => setForm(f => ({ ...f, project: e.target.value }))}
              placeholder="my-project"
              required
              data-testid="ingest-project-input"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">来源类型</label>
            <select
              className="input w-full"
              value={form.source_type}
              onChange={e => setForm(f => ({ ...f, source_type: e.target.value }))}
            >
              <option value="markdown">markdown</option>
              <option value="text">text</option>
              <option value="json">json</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">内容</label>
          <textarea
            className="input w-full min-h-[120px] font-mono text-sm"
            value={form.content}
            onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
            placeholder="输入要摄入的 Markdown 内容..."
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={ingest.isPending}
          data-testid="ingest-submit-btn"
        >
          {ingest.isPending ? '摄入中...' : '🚀 开始摄入'}
        </button>
      </form>

      {/* Log */}
      {log.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-4" data-testid="ingest-log">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">摄入日志</span>
            <button
              className="text-xs text-gray-500 hover:text-gray-300"
              onClick={() => setLog([])}
            >
              清空
            </button>
          </div>
          <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap max-h-64 overflow-y-auto">
            {log.join('\n')}
          </pre>
        </div>
      )}
    </div>
  )
}
