import { create } from 'zustand'

interface GenerationState {
  jobStatus: string
  logs: string[]
  streamBuffer: string
  streamKey: string
  stageStatuses: Record<string, string>
  pendingReview: any | null
  setJobStatus: (status: string) => void
  addLog: (msg: string) => void
  setStreamBuffer: (fn: (prev: string) => string) => void
  appendStreamChunk: (text: string, chapter?: number, scene?: number) => void
  clearStreamBuffer: () => void
  setStageStatus: (stage: string, status: string) => void
  setPendingReview: (review: any | null) => void
  reset: () => void
}

export const useGenerationStore = create<GenerationState>((set) => ({
  jobStatus: 'idle',
  logs: [],
  streamBuffer: '',
  streamKey: '',
  stageStatuses: {},
  pendingReview: null,

  setJobStatus: (status) => set({ jobStatus: status }),
  addLog: (msg) => set((s) => ({ logs: [...s.logs.slice(-500), msg] })),
  setStreamBuffer: (fn) => set((s) => ({ streamBuffer: fn(s.streamBuffer) })),
  // Labels scene boundaries so the live preview reads as scenes, not one unbroken blob.
  appendStreamChunk: (text, chapter, scene) => set((s) => {
    const key = `${chapter ?? ''}:${scene ?? ''}`
    let buf = s.streamBuffer
    if (key !== s.streamKey && (chapter != null || scene != null)) {
      const label = scene != null ? `Chapter ${chapter ?? '?'} — Scene ${scene}` : `Chapter ${chapter}`
      buf += `${buf ? '\n\n' : ''}────── ${label} ──────\n\n`
    }
    return { streamBuffer: buf + (text || ''), streamKey: key }
  }),
  clearStreamBuffer: () => set({ streamBuffer: '', streamKey: '' }),
  setStageStatus: (stage, status) => set((s) => ({
    stageStatuses: { ...s.stageStatuses, [stage]: status },
  })),
  setPendingReview: (review) => set({ pendingReview: review }),
  reset: () => set({ jobStatus: 'idle', logs: [], streamBuffer: '', streamKey: '', stageStatuses: {}, pendingReview: null }),
}))
