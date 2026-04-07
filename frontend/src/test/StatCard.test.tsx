import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatCard from '@/components/StatCard'

describe('StatCard', () => {
  it('renders label', () => {
    render(<StatCard label="Wiki 页面" value={42} />)
    expect(screen.getByText('Wiki 页面')).toBeInTheDocument()
  })

  it('renders numeric value', () => {
    render(<StatCard label="测试" value={99} />)
    expect(screen.getByText('99')).toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    render(<StatCard label="测试" value={7} icon="🚀" />)
    expect(screen.getByText('🚀')).toBeInTheDocument()
  })

  it('has stat-card testid', () => {
    render(<StatCard label="x" value={0} />)
    expect(screen.getByTestId('stat-card')).toBeInTheDocument()
  })

  it('renders zero value', () => {
    render(<StatCard label="Zero" value={0} />)
    expect(screen.getByText('0')).toBeInTheDocument()
  })
})
