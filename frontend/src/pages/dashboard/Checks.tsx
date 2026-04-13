import { useMemo, useState } from 'react'
import { useChecks } from '@/api/useScheduler'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

type CheckType = 'docs' | 'profile' | 'plan'

const STATUS_STYLE: Record<string, string> = {
  pass: 'badge badge-green',
  warn: 'badge badge-yellow',
  fail: 'badge badge-red',
}

export default function Checks() {
  const [checkType, setCheckType] = useState<CheckType>('docs')
  const { data: checks, isLoading, error, refetch } = useChecks({ check_type: checkType })
  const results = useMemo(() => checks?.checks ?? [], [checks])

  return (
    <div className="space-y-6" data-testid="checks-page">
      <div className="flex items-center justify-between">
        <h1 className="page-title">合规检查</h1>
        <button
          className="btn btn-outline text-sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          🔄 刷新
        </button>
      </div>

      {/* Check type tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['docs', 'profile', 'plan'] as CheckType[]).map(t => (
          <button
            key={t}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              checkType === t
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setCheckType(t)}
          >
            {t}-check
          </button>
        ))}
      </div>

      {isLoading && <LoadingSpinner text={`执行 ${checkType}-check...`} />}
      {error && <ErrorAlert message="检查执行失败" />}

      {!isLoading && !error && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-3 gap-3">
            {(['pass', 'warn', 'fail'] as const).map(s => {
              const count = results.filter(r => r.status === s).length
              return (
                <div key={s} className="bg-white rounded-xl border border-gray-100 p-4 text-center">
                  <div className="text-2xl font-bold text-gray-800">{count}</div>
                  <div className={STATUS_STYLE[s] || 'badge badge-gray'}>{s}</div>
                </div>
              )
            })}
          </div>

          {/* Results list */}
          {results.length === 0 ? (
            <div className="bg-white rounded-xl border p-10 text-center text-gray-400">
              暂无检查结果
            </div>
          ) : (
            <div className="space-y-2">
              {results.map((r, i) => (
                <div
                    key={i}
                  className="bg-white rounded-xl border border-gray-100 p-4 flex items-center gap-3"
                  data-testid="check-result"
                >
                  <span className={STATUS_STYLE[r.status] ?? 'badge badge-gray'}>{r.status}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-700 truncate">{r.task_name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{r.project} · {r.check_type}-check · {r.summary}</p>
                    {r.details[0] && <p className="text-xs text-gray-400 mt-1 truncate">{r.details[0]}</p>}
                  </div>
                  {r.run_at && (
                    <span className="text-xs text-gray-400 flex-shrink-0">{formatDate(r.run_at)}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
