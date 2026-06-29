import { create } from 'zustand'

interface GenerationState {
  jobStatus: string
  logs: string[]
  streamBuffer: string
  stageStatuses: Record<string, string>
  pendingReview: any | null
  setJobStatus: (status: string) => void
  addLog: (msg: string) => void
  setStreamBuffer: (fn: (prev: string) => string) => void
  clearStreamBuffer: () => void
  setStageStatus: (stage: string, status: string) => void
  setPendingReview: (review: any | null) => void
  reset: () => void
}

export const useGenerationStore = create<GenerationState>((set) => ({
  jobStatus: 'idle',
  logs: [],
  streamBuffer: '',
  stageStatuses: {},
  pendingReview: null,

  setJobStatus: (status) => set({ jobStatus: status }),
  addLog: (msg) => set((s) => ({ logs: [...s.logs.slice(-500), msg] })),
  setStreamBuffer: (fn) => set((s) => ({ streamBuffer: fn(s.streamBuffer) })),
  clearStreamBuffer: () => set({ streamBuffer: '' }),
  setStageStatus: (stage, status) => set((s) => ({
    stageStatuses: { ...s.stageStatuses, [stage]: status },
  })),
  setPendingReview: (review) => set({ pendingReview: review }),
  reset: () => set({ jobStatus: 'idle', logs: [], streamBuffer: '', stageStatuses: {}, pendingReview: null }),
}))
