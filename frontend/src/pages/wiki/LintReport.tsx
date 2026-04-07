import { useWikiLint } from '@/api/useWiki'
import type { LintIssue as LintIssueType } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

const LEVEL_STYLE: Record<string, string> = {
  error: 'badge badge-red',
  warning: 'badge badge-yellow',
  info: 'badge badge-blue',
}

export default function LintReport() {
  const { data, isLoading, error } = useWikiLint()

  if (isLoading) return <LoadingSpinner text="加载 Lint 报告..." />
  if (error) return <ErrorAlert message="Lint 报告加载失败" />

  const issues: LintIssueType[] = data?.issues ?? []
  const total = data?.total ?? issues.length

  return (
    <div className="space-y-6" data-testid="lint-report-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Lint 报告</h1>
        <span className="text-sm text-gray-500">共 {total} 个 issue</span>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        {(['error', 'warning', 'info'] as const).map(lvl => {
          const count = issues.filter(i => (i.level ?? 'info') === lvl).length
          return (
            <div key={lvl} className="bg-white rounded-xl border border-gray-100 p-4 text-center">
              <div className="text-2xl font-bold text-gray-700">{count}</div>
              <span className={LEVEL_STYLE[lvl]}>{lvl}</span>
            </div>
          )
        })}
      </div>

      {issues.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-gray-500">没有 Lint 问题</p>
        </div>
      ) : (
        <div className="space-y-2">
          {issues.map((issue, i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-gray-100 p-4 flex items-start gap-3"
              data-testid="lint-issue"
            >
                <span className={LEVEL_STYLE[issue.level] ?? 'badge badge-gray'}>
                {issue.level}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono text-gray-500 mb-0.5">{issue.topic}</p>
                <p className="text-sm text-gray-800">{issue.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
