import { useQuery } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface ErrorRecord {
  id: string
  project?: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'open' | 'resolved'
  title: string
  created_at: string
  updated_at?: string
}

export interface ErrorsResponse {
  errors: ErrorRecord[]
  total: number
}

export interface ErrorDetail {
  id: string
  title: string
  status?: string
  project?: string
  content_html: string
  raw: string
  created_at?: string
}

export interface Rule {
  rule_id: string
  scope: string
  content: string
  status: 'active' | 'deprecated'
  created_at: string
}

export interface RulesResponse {
  rules: Rule[]
}

export interface SearchResultItem {
  type: 'error' | 'wiki' | 'workflow'
  id: string
  title: string
  snippet?: string
  score: number
  rerank_boost?: number
  rerank_reasons?: string[]
  matched_concepts?: Array<{
    id: string
    title: string
    node_type?: string
    score?: number
    primary_topic?: string
    project?: string
  }>
}

export interface SearchResultsResponse {
  query: string
  mode: string
  results: SearchResultItem[]
  total: number
}

export function useErrors(params?: { project?: string; severity?: string; status?: string }) {
  return useQuery<ErrorsResponse>({
    queryKey: ['errors', params],
    queryFn: async () => {
      const { data } = await client.get('/errors', { params })
      return data
    },
  })
}

export function useErrorDetail(id: string) {
  return useQuery<ErrorDetail>({
    queryKey: ['error-detail', id],
    queryFn: async () => {
      const { data } = await client.get(`/errors/${id}`)
      return data
    },
    enabled: Boolean(id?.trim()),
  })
}

export function useRules() {
  return useQuery<RulesResponse>({
    queryKey: ['rules'],
    queryFn: async () => {
      const { data } = await client.get('/rules')
      return data
    },
  })
}

export function useSearchResults(query: string) {
  return useQuery<SearchResultsResponse>({
    queryKey: ['search', query],
    queryFn: async () => {
      const { data } = await client.get('/search', { params: { q: query } })
      return data
    },
    enabled: Boolean(query?.trim()),
  })
}
