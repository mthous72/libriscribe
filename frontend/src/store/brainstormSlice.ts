import { create } from 'zustand'

export interface BrainstormFocus { type: string; name: string }

interface BrainstormState {
  open: boolean
  focus: BrainstormFocus | null
  // open the drawer; pass a focus to target a specific entity, omit to keep current
  openBrainstorm: (focus?: BrainstormFocus | null) => void
  close: () => void
  setFocus: (f: BrainstormFocus | null) => void
  // bumped whenever lore is written (e.g. brainstorm Apply-to-lore) so open views can refresh
  loreVersion: number
  bumpLore: () => void
}

export const useBrainstormStore = create<BrainstormState>((set) => ({
  open: false,
  focus: null,
  openBrainstorm: (focus) => set((s) => ({ open: true, focus: focus !== undefined ? focus : s.focus })),
  close: () => set({ open: false }),
  setFocus: (f) => set({ focus: f }),
  loreVersion: 0,
  bumpLore: () => set((s) => ({ loreVersion: s.loreVersion + 1 })),
}))
