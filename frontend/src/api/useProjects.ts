import { useQuery } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface Project {
  id: string
  name: string
  description?: string
  profile_path?: string
  health?: 'ok' | 'warn' | 'fail'
  wiki_count?: number
  error_count?: number
  rule_count?: number
  last_ingest?: string
}

export interface ProjectsResponse {
  projects: Project[]
}

export function useProjects() {
  return useQuery<ProjectsResponse>({
    queryKey: ['projects'],
    queryFn: async () => {
      const { data } = await client.get('/projects')
      return data
    },
  })
}

export function useProjectStats(id: string) {
  return useQuery({
    queryKey: ['projects', id, 'stats'],
    queryFn: async () => {
      const { data } = await client.get(`/projects/${id}/stats`)
      return data
    },
    enabled: Boolean(id),
  })
}
