import { create } from 'zustand'
import { reportUiState } from '../api/client'

interface UiState {
  /** True when there are unsaved edits to the book/lore somewhere in the app. */
  dirty: boolean
  markDirty: () => void
  markClean: () => void
}

// Debounce backend reports so rapid typing doesn't spam POST /api/ui-state.
let reportTimer: ReturnType<typeof setTimeout> | null = null
function reportDirty(dirty: boolean) {
  if (reportTimer) clearTimeout(reportTimer)
  reportTimer = setTimeout(() => {
    reportUiState({ dirty }).catch(() => {})
  }, 300)
}

export const useUiStore = create<UiState>((set, get) => ({
  dirty: false,
  markDirty: () => {
    if (!get().dirty) {
      set({ dirty: true })
      reportDirty(true)
    }
  },
  markClean: () => {
    if (get().dirty) {
      set({ dirty: false })
      reportDirty(false)
    }
  },
}))
