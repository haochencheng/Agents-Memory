import { useQuery } from '@tanstack/react-query'
import client from '@/lib/api-client'

export interface Stats {
  wiki_count: number
  error_count: number
  ingest_count: number
  projects: string[]
}

export function useStats() {
  return useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: async () => {
      const { data } = await client.get('/stats')
      return data
    },
  })
}
