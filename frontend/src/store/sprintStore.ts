import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type SprintConfig = {
  goal: string
  capacity: number
  riskThreshold: number
  selectedSkills: string[]
}

interface SprintStore {
  teamId: string | null
  uploadId: string | null
  sprintId: string | null
  planId: string | null
  currentJobId: string | null
  sprintConfig: SprintConfig
  setTeamId: (id: string | null) => void
  setUploadId: (id: string | null) => void
  setSprintId: (id: string | null) => void
  setPlanId: (id: string | null) => void
  setCurrentJobId: (id: string | null) => void
  setSprintConfig: (config: Partial<SprintConfig>) => void
  resetWorkflow: () => void
}

const defaultConfig: SprintConfig = {
  goal: 'Deliver highest-value stories within sprint constraints.',
  capacity: 30,
  riskThreshold: 0.7,
  selectedSkills: ['Backend', 'Frontend'],
}

export const useSprintStore = create<SprintStore>()(
  persist(
    (set) => ({
      teamId: null,
      uploadId: null,
      sprintId: null,
      planId: null,
      currentJobId: null,
      sprintConfig: defaultConfig,
      setTeamId: (teamId) => set({ teamId }),
      setUploadId: (uploadId) => set({ uploadId }),
      setSprintId: (sprintId) => set({ sprintId }),
      setPlanId: (planId) => set({ planId }),
      setCurrentJobId: (currentJobId) => set({ currentJobId }),
      setSprintConfig: (config) => set((state) => ({ sprintConfig: { ...state.sprintConfig, ...config } })),
      resetWorkflow: () =>
        set((state) => ({
          teamId: state.teamId,
          uploadId: null,
          sprintId: null,
          planId: null,
          currentJobId: null,
          sprintConfig: defaultConfig,
        })),
    }),
    {
      name: 'apex-sprint-store',
      partialize: (state) => ({
        teamId: state.teamId,
        uploadId: state.uploadId,
        sprintId: state.sprintId,
        planId: state.planId,
        currentJobId: state.currentJobId,
        sprintConfig: state.sprintConfig,
      }),
    },
  ),
)
