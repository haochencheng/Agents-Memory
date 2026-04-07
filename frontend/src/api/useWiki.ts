import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface WikiTopic {
  topic: string
  title: string
  tags: string[]
  word_count: number
  updated_at: string
}

export interface WikiTopicDetail extends WikiTopic {
  content_html: string
  raw: string
  frontmatter: Record<string, unknown>
}

export interface WikiListResponse {
  topics: WikiTopic[]
}

export interface LintIssue {
  topic: string
  line: number
  level: 'warning' | 'info' | 'error'
  message: string
}

export interface LintResponse {
  issues: LintIssue[]
  total: number
}

export interface GraphResponse {
  nodes: Array<{ id: string; title: string; project?: string; word_count?: number }>
  edges: Array<{ source: string; target: string; type?: string }>
}

export function useWikiList() {
  return useQuery<WikiListResponse>({
    queryKey: ['wiki'],
    queryFn: async () => {
      const { data } = await client.get('/wiki')
      return data
    },
  })
}

export function useWikiTopic(topic: string) {
  return useQuery<WikiTopicDetail>({
    queryKey: ['wiki', topic],
    queryFn: async () => {
      const { data } = await client.get(`/wiki/${topic}`)
      return data
    },
    enabled: Boolean(topic),
  })
}

export function useWikiLint() {
  return useQuery<LintResponse>({
    queryKey: ['wiki', 'lint'],
    queryFn: async () => {
      const { data } = await client.get('/wiki/lint')
      return data
    },
  })
}

export function useWikiGraph() {
  return useQuery<GraphResponse>({
    queryKey: ['wiki', 'graph'],
    queryFn: async () => {
      const { data } = await client.get('/wiki/graph')
      return data
    },
  })
}

export function useUpdateWikiTopic(topic: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (compiledTruth: string) => {
      const { data } = await client.put(`/wiki/${topic}`, { compiled_truth: compiledTruth })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wiki', topic] })
    },
  })
}

export function useCompileTopic(topic: string) {
  return useMutation({
    mutationFn: async () => {
      const { data } = await client.post(`/wiki/${topic}/compile`)
      return data
    },
  })
}
