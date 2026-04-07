import { useState } from 'react'
import { useErrors, useRules } from '@/api/useMemory'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatDate } from '@/lib/utils'

type Tab = 'errors' | 'rules'

export default function MemoryRecords() {
  const [tab, setTab] = useState<Tab>('errors')
  const { data: errors, isLoading: errLoading, error: errError } = useErrors()
  const { data: rules, isLoading: rulesLoading, error: rulesError } = useRules()

  const isLoading = tab === 'errors' ? errLoading : rulesLoading
  const err = tab === 'errors' ? errError : rulesError

  return (
    <div className="space-y-6" data-testid="memory-records-page">
      <h1 className="page-title">记忆记录</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['errors', 'rules'] as Tab[]).map(t => (
          <button
            key={t}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setTab(t)}
          >
            {t === 'errors' ? '🐛 错误记录' : '📋 规则'}
          </button>
        ))}
      </div>

      {isLoading && <LoadingSpinner text="加载中..." />}
      {err && <ErrorAlert message="数据加载失败" />}

      {/* Errors */}
      {tab === 'errors' && !isLoading && !err && (
        <div className="space-y-3">
          {(!errors?.errors || errors.errors.length === 0) ? (
            <div className="bg-white rounded-xl border p-10 text-center text-gray-400">暂无错误记录</div>
          ) : (
            errors.errors.map((e, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid="error-record">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{e.title}</p>
                    {e.project && <span className="badge badge-blue mt-1">{e.project}</span>}
                  </div>
                  <span className="text-xs text-gray-400 flex-shrink-0">{formatDate(e.created_at)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Rules */}
      {tab === 'rules' && !isLoading && !err && (
        <div className="space-y-3">
          {(!rules?.rules || rules.rules.length === 0) ? (
            <div className="bg-white rounded-xl border p-10 text-center text-gray-400">暂无规则</div>
          ) : (
            rules.rules.map((r, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid="rule-record">
                <p className="text-sm text-gray-800 font-mono">{r.content}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
