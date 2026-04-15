import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { PlanStatus } from '../types'

export function usePlanStatus(jobId: string | null) {
  return useQuery<PlanStatus>({
    queryKey: ['planStatus', jobId],
    queryFn: async () => {
      const { data } = await api.get<PlanStatus>(`/api/v1/plans/status/${jobId}`)
      return data
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.status === 'complete' || data?.status === 'failed' ? false : 2000
    },
  })
}
