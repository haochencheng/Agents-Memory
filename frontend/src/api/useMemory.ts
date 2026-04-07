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

export function useErrors(params?: { project?: string; severity?: string; status?: string }) {
  return useQuery<ErrorsResponse>({
    queryKey: ['errors', params],
    queryFn: async () => {
      const { data } = await client.get('/errors', { params })
      return data
    },
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
  return useQuery({
    queryKey: ['search', query],
    queryFn: async () => {
      const { data } = await client.get('/search', { params: { q: query } })
      return data
    },
    enabled: Boolean(query?.trim()),
  })
}
