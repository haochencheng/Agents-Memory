import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface SchedulerTask {
  id: string
  name: string
  check_type: 'docs' | 'profile' | 'plan'
  project: string
  cron_expr: string
  status: 'active' | 'paused'
  created_at?: string
  updated_at?: string
  last_run?: string
  next_run?: string
  last_result?: 'pass' | 'warn' | 'fail'
  last_summary?: string
}

export interface CheckResult {
  id: string
  task_id: string
  task_name: string
  project: string
  check_type: 'docs' | 'profile' | 'plan'
  status: 'pass' | 'warn' | 'fail'
  run_at: string
  duration_ms: number
  summary: string
  details: string[]
}

export interface ChecksResponse {
  checks: CheckResult[]
  total: number
}

export interface ChecksSummaryResponse {
  docs_pass: number
  docs_warn: number
  docs_fail: number
  profile_pass: number
  profile_warn: number
  profile_fail: number
  plan_pass: number
  plan_warn: number
  plan_fail: number
}

export function useSchedulerTasks() {
  return useQuery<{ tasks: SchedulerTask[] }>({
    queryKey: ['scheduler', 'tasks'],
    queryFn: async () => {
      const { data } = await client.get('/scheduler/tasks')
      return data
    },
  })
}

export function useCreateSchedulerTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (task: { name: string; project: string; cron_expr: string }) => {
      const { data } = await client.post('/scheduler/tasks', task)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler'] }),
  })
}

export function useDeleteSchedulerTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await client.delete(`/scheduler/tasks/${id}`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler'] }),
  })
}

export function useChecks(params?: { project?: string; check_type?: string; status?: string }) {
  return useQuery<ChecksResponse>({
    queryKey: ['checks', params],
    queryFn: async () => {
      const { data } = await client.get('/checks', { params })
      return data
    },
  })
}

export function useChecksSummary() {
  return useQuery<ChecksSummaryResponse>({
    queryKey: ['checks', 'summary'],
    queryFn: async () => {
      const { data } = await client.get('/checks/summary')
      return data
    },
  })
}

export function useIngest() {
  return useMutation({
    mutationFn: async (payload: { project: string; source_type: string; content: string; tags?: string[]; dry_run?: boolean }) => {
      const { data } = await client.post('/ingest', payload)
      return data
    },
  })
}

export function useIngestLog() {
  return useQuery({
    queryKey: ['ingest', 'log'],
    queryFn: async () => {
      const { data } = await client.get('/ingest/log')
      return data
    },
  })
}
