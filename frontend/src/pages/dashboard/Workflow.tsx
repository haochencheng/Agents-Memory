import { useProjects } from '@/api/useProjects'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import WorkflowStepper from '@/components/WorkflowStepper'

const WORKFLOW_STEPS = [
  { key: 'ingest', label: '摄入' },
  { key: 'parse', label: '解析' },
  { key: 'lint', label: 'Lint' },
  { key: 'check', label: 'Check' },
  { key: 'store', label: '存储' },
]

// Derive step status from project data (mocked as complete for now)
function getStepStatus(step: string): 'done' | 'active' | 'pending' | 'failed' {
  // In a real scenario, this would check actual workflow state
  const doneSteps = ['ingest', 'parse']
  const activeSteps = ['lint']
  if (doneSteps.includes(step)) return 'done'
  if (activeSteps.includes(step)) return 'active'
  return 'pending'
}

export default function Workflow() {
  const { data: projects, isLoading, error } = useProjects()

  const steps = WORKFLOW_STEPS.map(s => ({ ...s, status: getStepStatus(s.key) }))

  return (
    <div className="space-y-6" data-testid="workflow-page">
      <h1 className="page-title">Workflow 状态</h1>

      {isLoading && <LoadingSpinner text="加载工作流状态..." />}
      {error && <ErrorAlert message="工作流数据加载失败" />}

      {!isLoading && !error && (!projects?.projects || projects.projects.length === 0) && (
        <div className="bg-white rounded-xl border border-gray-100 p-12 text-center">
          <div className="text-4xl mb-3">🔄</div>
          <p className="text-gray-500">暂无工作流记录</p>
        </div>
      )}
      {!isLoading && !error && projects?.projects && projects.projects.length > 0 && (
        <div className="space-y-4">
          {projects.projects.map(p => (
            <div key={p.name} className="bg-white rounded-xl border border-gray-100 p-5">
              <h3 className="font-semibold text-gray-700 mb-4 font-mono">{p.name}</h3>
              <WorkflowStepper steps={steps} />
            </div>
          ))}
        </div>
      )}

      {/* Workflow description */}
      <div className="bg-blue-50 rounded-xl border border-blue-100 p-5">
        <h2 className="section-title text-blue-800">工作流说明</h2>
        <ol className="list-decimal list-inside space-y-1 text-sm text-blue-700 mt-2">
          <li><strong>摄入</strong>：读取项目文件，识别文档/错误/规则等资产</li>
          <li><strong>解析</strong>：提取 Markdown 结构，关联引用</li>
          <li><strong>Lint</strong>：检查文档质量，生成 issue 列表</li>
          <li><strong>Check</strong>：执行 docs/profile/plan 合规检查</li>
          <li><strong>存储</strong>：写入 wiki 和记忆文件</li>
        </ol>
      </div>
    </div>
  )
}
