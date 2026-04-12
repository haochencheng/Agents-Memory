import { useQuery } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface WorkflowRecord {
  id: string
  title: string
  source_type: string
  project: string
  status: string
  created_at: string
  storage_kind: string
}

export interface WorkflowResponse {
  records: WorkflowRecord[]
  total: number
}

export interface WorkflowDetail extends WorkflowRecord {
  content_html: string
  raw: string
}

export function useWorkflowRecords(params?: { project?: string; source_type?: string; limit?: number }) {
  return useQuery<WorkflowResponse>({
    queryKey: ['workflow', params],
    queryFn: async () => {
      const { data } = await client.get('/workflow', { params })
      return data
    },
  })
}

export function useWorkflowRecord(id: string) {
  return useQuery<WorkflowDetail>({
    queryKey: ['workflow-detail', id],
    queryFn: async () => {
      const { data } = await client.get(`/workflow/${id}`)
      return data
    },
    enabled: Boolean(id?.trim()),
  })
}
