import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface SchedulerTask {
  id: string
  name: string
  check_type: 'docs' | 'profile' | 'plan'
  project: string
  cron_expr: string
  status: 'active' | 'paused'
  last_run?: string
  next_run?: string
  last_result?: 'pass' | 'warn' | 'fail'
}

export interface TaskHistoryEntry {
  run_at: string
  duration_ms: number
  result: 'pass' | 'warn' | 'fail'
  summary: string
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
    mutationFn: async (task: Omit<SchedulerTask, 'id' | 'status' | 'last_run' | 'next_run' | 'last_result'>) => {
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
  return useQuery({
    queryKey: ['checks', params],
    queryFn: async () => {
      const { data } = await client.get('/checks', { params })
      return data
    },
  })
}

export function useChecksSummary() {
  return useQuery({
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
