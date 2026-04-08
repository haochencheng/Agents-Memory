import { useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface ProjectKnowledgeSource {
  source_path: string
  topic: string
}

export interface ProjectOnboardingResponse {
  success: boolean
  project_id: string
  project_root: string
  full: boolean
  ingest_wiki: boolean
  dry_run: boolean
  enable_exit_code: number
  enable_log: string
  discovered_files: string[]
  ingested_files: number
  wiki_topics: string[]
  sources: ProjectKnowledgeSource[]
}

export function useProjectOnboarding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      project_root: string
      full: boolean
      ingest_wiki: boolean
      max_files?: number | null
      dry_run?: boolean
    }) => {
      const { data } = await client.post('/onboarding/bootstrap', payload)
      return data as ProjectOnboardingResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['wiki'] })
      queryClient.invalidateQueries({ queryKey: ['ingest'] })
    },
  })
}