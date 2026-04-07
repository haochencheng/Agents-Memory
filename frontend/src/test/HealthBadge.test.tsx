import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import HealthBadge from '@/components/HealthBadge'

describe('HealthBadge', () => {
  it('shows healthy text', () => {
    render(<HealthBadge status="healthy" />)
    expect(screen.getByText(/healthy/i)).toBeInTheDocument()
  })

  it('shows warning text', () => {
    render(<HealthBadge status="warning" />)
    expect(screen.getByText(/warning/i)).toBeInTheDocument()
  })

  it('shows error text', () => {
    render(<HealthBadge status="error" />)
    expect(screen.getByText(/error/i)).toBeInTheDocument()
  })

  it('shows unknown text for unrecognized status', () => {
    render(<HealthBadge status="unknown" />)
    expect(screen.getByText(/unknown/i)).toBeInTheDocument()
  })

  it('has health-badge testid', () => {
    render(<HealthBadge status="healthy" />)
    expect(screen.getByTestId('health-badge')).toBeInTheDocument()
  })
})
