import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import WikiCard from '@/components/WikiCard'

const TOPIC = {
  topic: 'Getting Started',
  title: 'Getting Started',
  summary: 'Quick start guide',
  tags: ['onboarding', 'setup'],
  word_count: 450,
  updated_at: '2024-03-01T00:00:00Z',
  project: 'demo-project',
  source_path: 'README.md',
}

describe('WikiCard', () => {
  const renderWikiCard = () =>
    render(
      <MemoryRouter>
        <WikiCard topic={TOPIC} />
      </MemoryRouter>
    )

  it('renders topic name', () => {
    renderWikiCard()
    expect(screen.getByText('Getting Started')).toBeInTheDocument()
  })

  it('renders topic name as title', () => {
    renderWikiCard()
    expect(screen.getByText('Getting Started')).toBeInTheDocument()
  })

  it('renders tags', () => {
    renderWikiCard()
    expect(screen.getByText('onboarding')).toBeInTheDocument()
    expect(screen.getByText('setup')).toBeInTheDocument()
  })

  it('renders word count', () => {
    renderWikiCard()
    expect(screen.getByText(/450/)).toBeInTheDocument()
  })

  it('has wiki-card testid', () => {
    renderWikiCard()
    expect(screen.getByTestId('wiki-card')).toBeInTheDocument()
  })
})
