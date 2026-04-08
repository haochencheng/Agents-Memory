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

export interface ProjectStats {
  id: string
  health: 'ok' | 'warn' | 'fail' | 'unknown'
  wiki_count: number
  error_count: number
  checklist_done: number
  ingest_count: number
  last_error: string
  last_ingest: string
}

export interface ProjectWikiNavItem {
  topic: string
  title: string
  source_path: string
  nav_path: string
  source_group: string
  document_role: string
  updated_at: string
  word_count: number
}

export interface ProjectWikiNavNode {
  key: string
  label: string
  path: string
  depth: number
  item_count: number
  topics: ProjectWikiNavItem[]
  children: ProjectWikiNavNode[]
}

export interface ProjectWikiNavGroup {
  key: string
  label: string
  item_count: number
  topics: ProjectWikiNavItem[]
}

export interface ProjectWikiNavResponse {
  project_id: string
  total_topics: number
  items: ProjectWikiNavItem[]
  tree: ProjectWikiNavNode[]
  groups: ProjectWikiNavGroup[]
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
  return useQuery<ProjectStats>({
    queryKey: ['projects', id, 'stats'],
    queryFn: async () => {
      const { data } = await client.get(`/projects/${id}/stats`)
      return data
    },
    enabled: Boolean(id),
  })
}

export function useProjectWikiNav(id: string) {
  return useQuery<ProjectWikiNavResponse>({
    queryKey: ['projects', id, 'wiki-nav'],
    queryFn: async () => {
      const { data } = await client.get(`/projects/${id}/wiki-nav`)
      return data
    },
    enabled: Boolean(id),
  })
}
