import { create } from 'zustand'

// B45: the workbench's selection model — every KB object is addressable as a NodeRef.
export type NodeRef =
  | { kind: 'concept' }
  | { kind: 'outline' }
  | { kind: 'world' }
  | { kind: 'chapter', n: number }
  | { kind: 'scene', chapter: number, scene: number }
  | { kind: 'character' | 'location' | 'lore' | 'thread' | 'arc', name: string }
  | { kind: 'milestone', arc: string, index: number }

// NodeRef ↔ `?sel=` URL param (deep-linkable selections: scene:3.2, character:Maren).
export function serializeNodeRef(ref: NodeRef): string {
  switch (ref.kind) {
    case 'concept': case 'outline': case 'world': return ref.kind
    case 'chapter': return `chapter:${ref.n}`
    case 'scene': return `scene:${ref.chapter}.${ref.scene}`
    case 'milestone': return `milestone:${encodeURIComponent(ref.arc)}.${ref.index}`
    default: return `${ref.kind}:${encodeURIComponent(ref.name)}`
  }
}

export function parseNodeRef(s: string | null): NodeRef | null {
  if (!s) return null
  if (s === 'concept' || s === 'outline' || s === 'world') return { kind: s }
  const i = s.indexOf(':')
  if (i < 0) return null
  const kind = s.slice(0, i)
  const rest = s.slice(i + 1)
  if (kind === 'chapter') {
    const n = parseInt(rest)
    return Number.isFinite(n) ? { kind: 'chapter', n } : null
  }
  if (kind === 'scene') {
    const [c, sc] = rest.split('.').map(Number)
    return Number.isFinite(c) && Number.isFinite(sc) ? { kind: 'scene', chapter: c, scene: sc } : null
  }
  if (kind === 'milestone') {
    const dot = rest.lastIndexOf('.')
    const idx = parseInt(rest.slice(dot + 1))
    if (dot < 0 || !Number.isFinite(idx)) return null
    return { kind: 'milestone', arc: decodeURIComponent(rest.slice(0, dot)), index: idx }
  }
  if (kind === 'character' || kind === 'location' || kind === 'lore' || kind === 'thread' || kind === 'arc') {
    return { kind, name: decodeURIComponent(rest) }
  }
  return null
}

export function sameNodeRef(a: NodeRef | null, b: NodeRef | null): boolean {
  if (!a || !b) return a === b
  return serializeNodeRef(a) === serializeNodeRef(b)
}

const PANE_KEY = 'libriscribe.workbench.panes'

function loadPaneWidths(): [number, number] {
  try {
    const raw = localStorage.getItem(PANE_KEY)
    if (raw) {
      const [l, r] = JSON.parse(raw)
      if (Number.isFinite(l) && Number.isFinite(r)) return [l, r]
    }
  } catch {}
  return [260, 360]
}

interface WorkbenchState {
  selection: NodeRef | null
  setSelection: (ref: NodeRef | null) => void
  focusFollow: boolean            // brainstorm focus follows tree selection (Slice 2)
  setFocusFollow: (v: boolean) => void
  paneWidths: [number, number]    // left / right px, persisted
  setPaneWidths: (w: [number, number]) => void
  rightOpen: boolean              // brainstorm pane collapsed/open
  setRightOpen: (v: boolean) => void
  treeVersion: number             // bump to refetch tree data after edits
  bumpTree: () => void
}

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  selection: null,
  setSelection: (ref) => set({ selection: ref }),
  focusFollow: true,
  setFocusFollow: (v) => set({ focusFollow: v }),
  paneWidths: loadPaneWidths(),
  setPaneWidths: (w) => {
    try { localStorage.setItem(PANE_KEY, JSON.stringify(w)) } catch {}
    set({ paneWidths: w })
  },
  rightOpen: true,
  setRightOpen: (v) => set({ rightOpen: v }),
  treeVersion: 0,
  bumpTree: () => set(s => ({ treeVersion: s.treeVersion + 1 })),
}))
