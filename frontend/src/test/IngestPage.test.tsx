import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Ingest from '@/pages/wiki/Ingest'

const ingestMutateAsync = vi.fn()
const onboardingMutateAsync = vi.fn()

vi.mock('@/api/useScheduler', () => ({
  useIngest: () => ({
    isPending: false,
    mutateAsync: ingestMutateAsync,
  }),
}))

vi.mock('@/api/useOnboarding', () => ({
  useProjectOnboarding: () => ({
    isPending: false,
    mutateAsync: onboardingMutateAsync,
  }),
}))

describe('Ingest page', () => {
  beforeEach(() => {
    ingestMutateAsync.mockReset()
    onboardingMutateAsync.mockReset()
  })

  it('renders project onboarding controls', () => {
    render(<Ingest />)
    expect(screen.getByTestId('project-onboarding-form')).toBeInTheDocument()
    expect(screen.getByTestId('onboarding-root-input')).toBeInTheDocument()
    expect(screen.getByTestId('project-onboarding-submit')).toBeInTheDocument()
  })

  it('submits project onboarding request', async () => {
    onboardingMutateAsync.mockResolvedValue({
      project_id: 'synapse-network',
      enable_exit_code: 0,
      enable_log: 'ok',
      ingested_files: 2,
      wiki_topics: ['synapse-network-readme', 'synapse-network-agents'],
      sources: [
        { source_path: 'README.md', topic: 'synapse-network-readme' },
        { source_path: 'AGENTS.md', topic: 'synapse-network-agents' },
      ],
    })
    const user = userEvent.setup()
    render(<Ingest />)

    await user.type(screen.getByTestId('onboarding-root-input'), '/tmp/Synapse-Network')
    await user.click(screen.getByTestId('project-onboarding-submit'))

    expect(onboardingMutateAsync).toHaveBeenCalledWith({
      project_root: '/tmp/Synapse-Network',
      full: true,
      ingest_wiki: true,
      max_files: null,
    })
    expect(await screen.findByText(/项目接入完成/)).toBeInTheDocument()
  })
})