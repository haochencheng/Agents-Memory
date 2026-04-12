import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface WikiTopic {
  topic: string
  title: string
  tags: string[]
  doc_type?: string
  word_count: number
  updated_at: string
  project: string
  source_path: string
}

export interface WikiTopicDetail extends WikiTopic {
  content_html: string
  raw: string
  frontmatter: Record<string, unknown>
  links: TopicRelation[]
  backlinks: TopicRelation[]
  related_topics: TopicRelation[]
}

export interface WikiListResponse {
  topics: WikiTopic[]
  total: number
  page: number
  page_size: number
  total_pages: number
  query: string
}

export interface WikiListQuery {
  query?: string
  page?: number
  pageSize?: number
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
  nodes: Array<{ id: string; title: string; node_type?: string; project?: string; word_count?: number; tags?: string[]; primary_topic?: string; topic_count?: number }>
  edges: Array<{ source: string; target: string; type?: string; weight?: number }>
}

export interface TopicRelation {
  topic: string
  title: string
  relation: string
  reason: string
  score: number
  project: string
  tags: string[]
}

export function useWikiList(params: WikiListQuery = {}) {
  const query = params.query ?? ''
  const page = params.page ?? 1
  const pageSize = params.pageSize ?? 20

  return useQuery<WikiListResponse>({
    queryKey: ['wiki', { query, page, pageSize }],
    queryFn: async () => {
      const { data } = await client.get('/wiki', {
        params: {
          q: query || undefined,
          page,
          page_size: pageSize,
        },
      })
      return data
    },
  })
}

export function useWikiTopic(topic: string) {
  return useWikiTopicWithOptions(topic)
}

export function useWikiTopicWithOptions(topic: string, options?: { enabled?: boolean }) {
  return useQuery<WikiTopicDetail>({
    queryKey: ['wiki', topic],
    queryFn: async () => {
      const { data } = await client.get(`/wiki/${topic}`)
      return data
    },
    enabled: Boolean(topic) && (options?.enabled ?? true),
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
