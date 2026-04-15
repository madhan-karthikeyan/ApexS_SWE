import { useMutation } from '@tanstack/react-query'
import { api } from '../utils/api'

export function useDatasetUpload() {
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await api.post('/api/v1/datasets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
  })
}
