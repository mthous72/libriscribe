import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { NodeRef } from '../store/workbenchSlice'
import { serializeNodeRef, sameNodeRef } from '../store/workbenchSlice'

function labelFor(ref: NodeRef): string {
  switch (ref.kind) {
    case 'concept': return 'Concept'
    case 'outline': return 'Outline'
    case 'world': return 'World'
    case 'chapter': return `Chapter ${ref.n}`
    case 'scene': return `Scene ${ref.chapter}.${ref.scene}`
    case 'milestone': return `Milestone ${ref.index + 1} — ${ref.arc}`
    default: return `${ref.kind[0].toUpperCase()}${ref.kind.slice(1)}: ${ref.name}`
  }
}

// B45: walk the story one item at a time. Order comes from buildNavOrder (story spine first,
// then section-local sequences).
export default function PrevNextBar({ order, selection, onSelect }: {
  order: NodeRef[], selection: NodeRef | null, onSelect: (ref: NodeRef) => void,
}) {
  const idx = selection ? order.findIndex(r => sameNodeRef(r, selection)) : -1
  const prev = idx > 0 ? order[idx - 1] : null
  const next = idx >= 0 && idx < order.length - 1 ? order[idx + 1] : null
  return (
    <div className="flex items-center justify-between gap-2 mb-3">
      <button disabled={!prev} onClick={() => prev && onSelect(prev)}
        className="flex items-center gap-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs disabled:opacity-40 min-w-0"
        title={prev ? labelFor(prev) : undefined}>
        <ChevronLeft size={14} className="shrink-0" />
        <span className="truncate">{prev ? labelFor(prev) : '—'}</span>
      </button>
      <span className="text-xs text-gray-500 shrink-0" title={selection ? serializeNodeRef(selection) : ''}>
        {idx >= 0 ? `${idx + 1} / ${order.length}` : ''}
      </span>
      <button disabled={!next} onClick={() => next && onSelect(next)}
        className="flex items-center gap-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs disabled:opacity-40 min-w-0"
        title={next ? labelFor(next) : undefined}>
        <span className="truncate">{next ? labelFor(next) : '—'}</span>
        <ChevronRight size={14} className="shrink-0" />
      </button>
    </div>
  )
}
