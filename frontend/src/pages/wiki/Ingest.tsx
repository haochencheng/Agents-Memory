import { useState } from 'react'
import { useIngest } from '@/api/useScheduler'
import { useProjectOnboarding } from '@/api/useOnboarding'

interface IngestForm {
  project: string
  source_type: string
  content: string
}

interface OnboardingForm {
  project_root: string
  full: boolean
  ingest_wiki: boolean
  max_files: number
}

const EMPTY_FORM: IngestForm = { project: '', source_type: 'markdown', content: '' }
const EMPTY_ONBOARDING_FORM: OnboardingForm = {
  project_root: '',
  full: true,
  ingest_wiki: true,
  max_files: 24,
}

export default function Ingest() {
  const ingest = useIngest()
  const onboarding = useProjectOnboarding()
  const [form, setForm] = useState<IngestForm>(EMPTY_FORM)
  const [onboardingForm, setOnboardingForm] = useState<OnboardingForm>(EMPTY_ONBOARDING_FORM)
  const [log, setLog] = useState<string[]>([])
  const [formError, setFormError] = useState('')
  const [onboardingError, setOnboardingError] = useState('')

  const appendLog = (message: string) => {
    setLog(prev => [...prev, `[${new Date().toISOString()}] ${message}`])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.project.trim()) {
      setFormError('项目名称为必填')
      return
    }
    appendLog(`启动文本摄入: project=${form.project}`)
    try {
      const result = await ingest.mutateAsync({
        project: form.project,
        source_type: form.source_type,
        content: form.content,
      })
      const msg = typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result)
      appendLog(`[OK] ${msg}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      appendLog(`[ERR] ${msg}`)
      setFormError('摄入失败: ' + msg)
    }
  }

  const handleOnboardingSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setOnboardingError('')
    if (!onboardingForm.project_root.trim()) {
      setOnboardingError('项目路径为必填')
      return
    }
    appendLog(`启动项目自动接入: root=${onboardingForm.project_root}`)
    try {
      const result = await onboarding.mutateAsync(onboardingForm)
      appendLog(`[OK] 项目接入完成: project=${result.project_id}, bootstrap_exit=${result.enable_exit_code}`)
      if (result.enable_log) {
        appendLog(`bootstrap log:\n${result.enable_log}`)
      }
      appendLog(`wiki 摄取: imported=${result.ingested_files}, topics=${result.wiki_topics.length}`)
      if (result.sources.length > 0) {
        appendLog(result.sources.map(item => `- ${item.source_path} -> ${item.topic}`).join('\n'))
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      appendLog(`[ERR] 项目自动接入失败: ${msg}`)
      setOnboardingError('项目自动接入失败: ' + msg)
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
            <label htmlFor="ingest-project-input" className="block text-xs text-gray-500 mb-1">项目名称 *</label>
            <input
              id="ingest-project-input"
              className="input w-full"
              value={form.project}
              onChange={e => setForm(f => ({ ...f, project: e.target.value }))}
              placeholder="my-project"
              required
              data-testid="ingest-project-input"
            />
          </div>
          <div>
            <label htmlFor="ingest-source-type" className="block text-xs text-gray-500 mb-1">来源类型</label>
            <select
              id="ingest-source-type"
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
          <label htmlFor="ingest-content" className="block text-xs text-gray-500 mb-1">内容</label>
          <textarea
            id="ingest-content"
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

      <form
        onSubmit={handleOnboardingSubmit}
        className="bg-white rounded-xl border border-gray-100 p-5 space-y-4"
        data-testid="project-onboarding-form"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="section-title">项目自动接入</h2>
            <p className="text-sm text-gray-500 mt-1">注册项目、应用接入工件，并可自动导入 README / AGENTS / docs Markdown 到共享 wiki。</p>
          </div>
          <span className="text-xs rounded-full bg-amber-50 text-amber-700 px-3 py-1">一键接入</span>
        </div>

        {onboardingError && (
          <p className="text-sm text-red-500 bg-red-50 rounded px-3 py-2">{onboardingError}</p>
        )}

        <div>
          <label htmlFor="onboarding-root-input" className="block text-xs text-gray-500 mb-1">项目路径 *</label>
          <input
            id="onboarding-root-input"
            className="input w-full font-mono text-sm"
            value={onboardingForm.project_root}
            onChange={e => setOnboardingForm(f => ({ ...f, project_root: e.target.value }))}
            placeholder="/Users/cliff/workspace/agent/Synapse-Network"
            data-testid="onboarding-root-input"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label htmlFor="onboarding-full" className="flex items-center gap-2 text-sm text-gray-700">
            <input
              id="onboarding-full"
              type="checkbox"
              checked={onboardingForm.full}
              onChange={e => setOnboardingForm(f => ({ ...f, full: e.target.checked }))}
            />
            <span>full 模式</span>
          </label>
          <label htmlFor="onboarding-ingest-wiki" className="flex items-center gap-2 text-sm text-gray-700">
            <input
              id="onboarding-ingest-wiki"
              type="checkbox"
              checked={onboardingForm.ingest_wiki}
              onChange={e => setOnboardingForm(f => ({ ...f, ingest_wiki: e.target.checked }))}
            />
            <span>自动摄取 wiki</span>
          </label>
          <div>
            <label htmlFor="onboarding-max-files" className="block text-xs text-gray-500 mb-1">最大导入文件数</label>
            <input
              id="onboarding-max-files"
              type="number"
              min={1}
              max={200}
              className="input w-full"
              value={onboardingForm.max_files}
              onChange={e => setOnboardingForm(f => ({ ...f, max_files: Number(e.target.value) || 1 }))}
            />
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={onboarding.isPending}
          data-testid="project-onboarding-submit"
        >
          {onboarding.isPending ? '接入中...' : '开始项目自动接入'}
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
