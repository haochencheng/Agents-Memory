import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import WorkflowStepper from '@/components/WorkflowStepper'

const STEPS = [
  { key: 'ingest', label: '摄入', status: 'done' as const },
  { key: 'parse', label: '解析', status: 'active' as const },
  { key: 'lint', label: 'Lint', status: 'pending' as const },
]

describe('WorkflowStepper', () => {
  it('renders all step labels', () => {
    render(<WorkflowStepper steps={STEPS} />)
    expect(screen.getByText('摄入')).toBeInTheDocument()
    expect(screen.getByText('解析')).toBeInTheDocument()
    expect(screen.getByText('Lint')).toBeInTheDocument()
  })

  it('has workflow-stepper testid', () => {
    render(<WorkflowStepper steps={STEPS} />)
    expect(screen.getByTestId('workflow-stepper')).toBeInTheDocument()
  })

  it('renders empty with no steps', () => {
    render(<WorkflowStepper steps={[]} />)
    expect(screen.getByTestId('workflow-stepper')).toBeInTheDocument()
  })
})
