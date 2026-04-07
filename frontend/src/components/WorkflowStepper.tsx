interface Step {
  key: string
  label: string
  status: 'done' | 'active' | 'pending' | 'failed'
}

interface WorkflowStepperProps {
  steps: Step[]
}

const statusIcon: Record<string, string> = {
  done: '✓',
  active: '⏳',
  failed: '✗',
  pending: '○',
}

const statusClass: Record<string, string> = {
  done: 'bg-green-500 text-white',
  active: 'bg-yellow-400 text-white animate-pulse',
  failed: 'bg-red-500 text-white',
  pending: 'bg-gray-200 text-gray-500',
}

export default function WorkflowStepper({ steps }: WorkflowStepperProps) {
  return (
    <div className="flex items-center gap-0" data-testid="workflow-stepper">
      {steps.map((step, i) => (
        <div key={step.key} className="flex items-center">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${statusClass[step.status]}`}>
              {statusIcon[step.status]}
            </div>
            <span className="text-xs text-gray-500 mt-1 whitespace-nowrap">{step.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-12 h-0.5 mx-1 mt-[-12px] ${step.status === 'done' ? 'bg-green-400' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}
