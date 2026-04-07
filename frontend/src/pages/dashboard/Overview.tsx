import StatCard from '@/components/StatCard'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { useStats } from '@/api/useStats'
import { useWikiLint } from '@/api/useWiki'
import { useChecksSummary } from '@/api/useScheduler'

function LintGauge({ total, issues }: { total: number; issues: number }) {
  const score = total > 0 ? Math.max(0, Math.round(((total - issues) / total) * 100)) : 100
  const color = score >= 90 ? 'text-green-600' : score >= 70 ? 'text-yellow-600' : 'text-red-600'
  return (
    <div className="flex flex-col items-center justify-center h-32" data-testid="lint-gauge">
      <div className={`text-5xl font-bold ${color}`}>{score}%</div>
      <div className="text-sm text-gray-500 mt-1">Wiki 健康分</div>
      <div className="text-xs text-gray-400">{issues} 个 issue</div>
    </div>
  )
}

export default function Overview() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useStats()
  const { data: lint } = useWikiLint()
  const { data: checks } = useChecksSummary()

  if (statsLoading) return <LoadingSpinner text="加载系统状态..." />
  if (statsError) return <ErrorAlert message="系统状态加载失败" />

  return (
    <div className="space-y-6" data-testid="overview-page">
      <h1 className="page-title">概览 Overview</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Wiki 页面" value={stats?.wiki_count ?? 0} icon="📚" />
        <StatCard label="错误记录" value={stats?.error_count ?? 0} icon="🐛" />
        <StatCard label="摄入次数" value={stats?.ingest_count ?? 0} icon="📥" />
        <StatCard label="接入项目" value={stats?.projects?.length ?? 0} icon="📁" />
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <h2 className="section-title">Wiki 健康度</h2>
          <LintGauge total={stats?.wiki_count ?? 0} issues={lint?.total ?? 0} />
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <h2 className="section-title">接入项目</h2>
          {(stats?.projects ?? []).length === 0 ? (
            <p className="text-sm text-gray-400 py-4 text-center">暂无项目</p>
          ) : (
            <ul className="space-y-1">
              {(stats?.projects ?? []).slice(0, 6).map(p => (
                <li key={p} className="flex items-center gap-2 text-sm py-1">
                  <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                  <span className="font-mono text-gray-700">{p}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Checks summary */}
      {checks && (
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <h2 className="section-title">Check 状态汇总</h2>
          <div className="grid grid-cols-3 gap-4">
            {['docs', 'profile', 'plan'].map(type => {
              const summary = (checks as Record<string, unknown>)[type] as { pass?: number; warn?: number; fail?: number } | undefined
              return (
                <div key={type} className="text-center">
                  <div className="text-sm font-medium text-gray-600 mb-2 capitalize">{type}-check</div>
                  <div className="flex justify-center gap-2">
                    <span className="badge badge-green">{summary?.pass ?? 0} pass</span>
                    <span className="badge badge-yellow">{summary?.warn ?? 0} warn</span>
                    <span className="badge badge-red">{summary?.fail ?? 0} fail</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
