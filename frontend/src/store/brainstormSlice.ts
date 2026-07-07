import { create } from 'zustand'

export interface BrainstormFocus { type: string; name: string }

interface BrainstormState {
  open: boolean
  /** The CURRENT session's focus (what the drawer is developing right now). */
  focus: BrainstormFocus | null
  /** An explicitly-requested object to brainstorm (e.g. from a lorebook "Brainstorm" button).
   *  The drawer resolves this to a per-object session; `pendingNonce` fires the resolver even when
   *  the requested object equals the current one (so the "same object" continue/new prompt shows). */
  pendingFocus: BrainstormFocus | null
  pendingNonce: number
  // open the drawer; pass a focus to target a specific entity, omit to just reveal the drawer
  openBrainstorm: (focus?: BrainstormFocus | null) => void
  close: () => void
  setFocus: (f: BrainstormFocus | null) => void
  clearPending: () => void
  // bumped whenever lore is written (e.g. brainstorm Apply-to-lore) so open views can refresh
  loreVersion: number
  bumpLore: () => void
}

export const useBrainstormStore = create<BrainstormState>((set) => ({
  open: false,
  focus: null,
  pendingFocus: null,
  pendingNonce: 0,
  openBrainstorm: (focus) => set((s) =>
    (focus !== undefined && focus !== null)
      ? { open: true, pendingFocus: focus, pendingNonce: s.pendingNonce + 1 }
      : { open: true }),
  close: () => set({ open: false }),
  setFocus: (f) => set({ focus: f }),
  clearPending: () => set({ pendingFocus: null }),
  loreVersion: 0,
  bumpLore: () => set((s) => ({ loreVersion: s.loreVersion + 1 })),
}))
