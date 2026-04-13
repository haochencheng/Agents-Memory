import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface SchedulerRunStep {
  id: string
  batch_id: string
  task_group_id: string
  check_type: 'docs' | 'profile' | 'plan'
  status: 'pass' | 'warn' | 'fail'
  duration_ms: number
  summary: string
  details: string[]
  workflow_record_id: string
}

export interface SchedulerRunBatch {
  id: string
  task_group_id: string
  task_group_name: string
  project: string
  run_at: string
  finished_at: string
  overall_status: 'pass' | 'warn' | 'fail'
  duration_ms: number
  trigger: 'scheduled' | 'manual'
  steps: SchedulerRunStep[]
}

export interface SchedulerTaskGroup {
  id: string
  name: string
  project: string
  cron_expr: string
  status: 'active' | 'paused'
  created_at?: string
  updated_at?: string
  last_run_at?: string
  next_run_at?: string
  last_result?: 'pass' | 'warn' | 'fail'
  last_summary?: string
  latest_steps: SchedulerRunStep[]
  recent_results: Array<'pass' | 'warn' | 'fail'>
}

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

export interface SchedulerTaskGroupsResponse {
  task_groups: SchedulerTaskGroup[]
  total: number
}

export interface SchedulerTaskGroupDetailResponse {
  task_group: SchedulerTaskGroup
  latest_batch: SchedulerRunBatch | null
}

export interface SchedulerRunListResponse {
  runs: SchedulerRunBatch[]
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

export function useSchedulerTaskGroups(params?: {
  q?: string
  project?: string
  status?: string
  last_result?: string
  failed_only?: boolean
}) {
  return useQuery<SchedulerTaskGroupsResponse>({
    queryKey: ['scheduler', 'task-groups', params],
    queryFn: async () => {
      const { data } = await client.get('/scheduler/task-groups', { params })
      return data
    },
  })
}

export function useSchedulerTaskGroup(id: string) {
  return useQuery<SchedulerTaskGroupDetailResponse>({
    queryKey: ['scheduler', 'task-groups', id],
    queryFn: async () => {
      const { data } = await client.get(`/scheduler/task-groups/${id}`)
      return data
    },
    enabled: Boolean(id),
  })
}

export function useSchedulerTaskGroupRuns(id: string) {
  return useQuery<SchedulerRunListResponse>({
    queryKey: ['scheduler', 'task-groups', id, 'runs'],
    queryFn: async () => {
      const { data } = await client.get(`/scheduler/task-groups/${id}/runs`)
      return data
    },
    enabled: Boolean(id),
  })
}

export function useCreateSchedulerTaskGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (task: { name: string; project: string; cron_expr: string }) => {
      const { data } = await client.post('/scheduler/task-groups', task)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler'] }),
  })
}

export function useUpdateSchedulerTaskGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { id: string; name: string; project: string; cron_expr: string; status: 'active' | 'paused' }) => {
      const { id, ...body } = payload
      const { data } = await client.put(`/scheduler/task-groups/${id}`, body)
      return data
    },
    onSuccess: (_data, payload) => {
      queryClient.invalidateQueries({ queryKey: ['scheduler'] })
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'task-groups', payload.id] })
    },
  })
}

export function usePauseSchedulerTaskGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await client.post(`/scheduler/task-groups/${id}/pause`)
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['scheduler'] })
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'task-groups', id] })
    },
  })
}

export function useResumeSchedulerTaskGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await client.post(`/scheduler/task-groups/${id}/resume`)
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['scheduler'] })
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'task-groups', id] })
    },
  })
}

export function useRunSchedulerTaskGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await client.post(`/scheduler/task-groups/${id}/run`)
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['scheduler'] })
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'task-groups', id] })
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'task-groups', id, 'runs'] })
      queryClient.invalidateQueries({ queryKey: ['checks'] })
    },
  })
}

export function useDeleteSchedulerTaskGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await client.delete(`/scheduler/task-groups/${id}`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler'] }),
  })
}

export function useCreateSchedulerTask() {
  return useCreateSchedulerTaskGroup()
}

export function useDeleteSchedulerTask() {
  return useDeleteSchedulerTaskGroup()
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
