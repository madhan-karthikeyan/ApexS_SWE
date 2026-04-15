import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'

export function useExplanations(planId: string | null) {
  return useQuery({
    queryKey: ['explanations', planId],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/plans/${planId}/explain`)
      return data
    },
    enabled: !!planId,
  })
}
