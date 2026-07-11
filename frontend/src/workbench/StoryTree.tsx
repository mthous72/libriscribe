import { useState } from 'react'
import { ChevronDown, ChevronRight, Mic } from 'lucide-react'
import type { WorkbenchTree } from '../api/client'
import { NodeRef, sameNodeRef } from '../store/workbenchSlice'

// B45 left pane: every KB object as a selectable node, in story order, with DERIVED status
// dots (green = written/complete, blue = developed/in progress, gray = pending).

function Dot({ tone }: { tone: 'done' | 'active' | 'pending' | 'warn' }) {
  const color = tone === 'done' ? 'bg-green-500' : tone === 'active' ? 'bg-blue-400'
    : tone === 'warn' ? 'bg-amber-400' : 'bg-gray-600'
  return <span className={`shrink-0 w-2 h-2 rounded-full ${color}`} />
}

function Row({ depth = 0, selected, onClick, children, title }: {
  depth?: number, selected: boolean, onClick: () => void, children: React.ReactNode, title?: string,
}) {
  return (
    <button onClick={onClick} title={title}
      style={{ paddingLeft: `${8 + depth * 14}px` }}
      className={`w-full flex items-center gap-2 pr-2 py-1.5 rounded-lg text-left text-sm truncate ${
        selected ? 'bg-indigo-900/70 border border-indigo-700' : 'hover:bg-gray-800 border border-transparent'
      }`}>
      {children}
    </button>
  )
}

function Section({ label, count, children, defaultOpen = false }: {
  label: string, count?: number, children: React.ReactNode, defaultOpen?: boolean,
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-1 px-1 py-1.5 text-[11px] uppercase tracking-wide text-gray-500 hover:text-gray-300">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {label}{typeof count === 'number' ? ` (${count})` : ''}
      </button>
      {open && <div className="space-y-0.5">{children}</div>}
    </div>
  )
}

export default function StoryTree({ tree, selection, onSelect }: {
  tree: WorkbenchTree, selection: NodeRef | null, onSelect: (ref: NodeRef) => void,
}) {
  const [openChapters, setOpenChapters] = useState<Set<number>>(new Set())
  const sel = (ref: NodeRef) => sameNodeRef(selection, ref)
  const stage = (k: string) => tree.stage_statuses?.[k] || ''
  const stageTone = (k: string): 'done' | 'active' | 'pending' =>
    stage(k) === 'complete' ? 'done' : stage(k) === 'in_progress' ? 'active' : 'pending'

  return (
    <div className="space-y-2 text-sm">
      {/* Story spine */}
      <div className="space-y-0.5">
        <Row selected={sel({ kind: 'concept' })} onClick={() => onSelect({ kind: 'concept' })}>
          <Dot tone={stageTone('concept')} /> <span className="font-medium">Concept</span>
        </Row>
        <Row selected={sel({ kind: 'outline' })} onClick={() => onSelect({ kind: 'outline' })}>
          <Dot tone={tree.outline_set ? 'done' : stageTone('outline')} /> <span className="font-medium">Outline</span>
        </Row>
      </div>

      <Section label="Chapters" count={tree.chapters.length} defaultOpen>
        {tree.chapters.map(ch => {
          const open = openChapters.has(ch.chapter_number)
          const tone = ch.has_file ? 'done' : (ch.summary_set && ch.scenes.length > 0) ? 'active' : 'pending'
          return (
            <div key={ch.chapter_number}>
              <div className="flex items-center">
                <button onClick={() => setOpenChapters(prev => {
                  const next = new Set(prev)
                  next.has(ch.chapter_number) ? next.delete(ch.chapter_number) : next.add(ch.chapter_number)
                  return next
                })} className="p-1 text-gray-500 hover:text-gray-300" aria-label="Toggle scenes">
                  {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                </button>
                <div className="flex-1 min-w-0">
                  <Row selected={sel({ kind: 'chapter', n: ch.chapter_number })}
                    onClick={() => onSelect({ kind: 'chapter', n: ch.chapter_number })}
                    title={ch.title || `Chapter ${ch.chapter_number}`}>
                    <Dot tone={tone} />
                    <span className="truncate">Ch. {ch.chapter_number}{ch.title ? ` — ${ch.title}` : ''}</span>
                    {ch.word_count > 0 && <span className="ml-auto text-[10px] text-gray-500 shrink-0">{ch.word_count}w</span>}
                  </Row>
                </div>
              </div>
              {open && ch.scenes.map(sc => (
                <Row key={sc.scene_number} depth={2}
                  selected={sel({ kind: 'scene', chapter: ch.chapter_number, scene: sc.scene_number })}
                  onClick={() => onSelect({ kind: 'scene', chapter: ch.chapter_number, scene: sc.scene_number })}>
                  <Dot tone={sc.has_prose ? 'done' : sc.summary_set ? 'active' : 'pending'} />
                  <span>Scene {sc.scene_number}</span>
                  {sc.word_count > 0 && <span className="ml-auto text-[10px] text-gray-500">{sc.word_count}w</span>}
                </Row>
              ))}
              {open && ch.scenes.length === 0 && (
                <div className="pl-9 py-1 text-[11px] text-gray-600">No scenes outlined yet</div>
              )}
            </div>
          )
        })}
      </Section>

      <Section label="Characters" count={tree.characters.length}>
        {tree.characters.map(c => (
          <Row key={c.name} depth={1} selected={sel({ kind: 'character', name: c.name })}
            onClick={() => onSelect({ kind: 'character', name: c.name })} title={c.role}>
            <Dot tone={c.fields_set >= 3 ? 'done' : c.fields_set > 0 ? 'active' : 'pending'} />
            <span className="truncate">{c.name}</span>
            {c.has_voice && <Mic size={11} className="ml-auto shrink-0 text-indigo-400" aria-label="Has voice profile" />}
          </Row>
        ))}
      </Section>

      <Section label="Locations" count={tree.locations.length}>
        {tree.locations.map(l => (
          <Row key={l.name} depth={1} selected={sel({ kind: 'location', name: l.name })}
            onClick={() => onSelect({ kind: 'location', name: l.name })}>
            <Dot tone="active" /><span className="truncate">{l.name}</span>
          </Row>
        ))}
      </Section>

      <Section label="Codex" count={tree.lore.length}>
        {tree.lore.map(e => (
          <Row key={e.name} depth={1} selected={sel({ kind: 'lore', name: e.name })}
            onClick={() => onSelect({ kind: 'lore', name: e.name })} title={e.entry_type}>
            <Dot tone="active" /><span className="truncate">{e.name}</span>
            {e.entry_type && <span className="ml-auto text-[10px] text-gray-500 shrink-0">{e.entry_type}</span>}
          </Row>
        ))}
      </Section>

      <div className="space-y-0.5">
        <Row selected={sel({ kind: 'world' })} onClick={() => onSelect({ kind: 'world' })}>
          <Dot tone={tree.worldbuilding_fields_set > 0 ? 'done' : 'pending'} />
          <span className="font-medium">World</span>
          {tree.worldbuilding_fields_set > 0 && <span className="ml-auto text-[10px] text-gray-500">{tree.worldbuilding_fields_set} fields</span>}
        </Row>
      </div>

      <Section label="Arcs" count={tree.arcs.length}>
        {tree.arcs.map(a => (
          <div key={a.name}>
            <Row depth={1} selected={sel({ kind: 'arc', name: a.name })}
              onClick={() => onSelect({ kind: 'arc', name: a.name })} title={a.arc_type}>
              <Dot tone={a.status === 'resolved' ? 'done' : 'active'} />
              <span className="truncate">{a.name}</span>
            </Row>
            {a.milestones.map((m: any, i: number) => (
              <Row key={i} depth={2} selected={sel({ kind: 'milestone', arc: a.name, index: i })}
                onClick={() => onSelect({ kind: 'milestone', arc: a.name, index: i })}
                title={m.proposal ? 'AI proposed a verdict — review it' : m.description}>
                <Dot tone={m.proposal ? 'warn' : m.status === 'completed' ? 'done' : m.status === 'in_progress' ? 'active' : 'pending'} />
                <span className="truncate text-xs">{m.name}</span>
                {m.proposal && <span className="ml-1 shrink-0 text-[9px] px-1 rounded bg-amber-900/70 text-amber-300">review</span>}
                {m.target_chapter && <span className="ml-auto text-[10px] text-gray-500 shrink-0">Ch.{m.target_chapter}</span>}
              </Row>
            ))}
          </div>
        ))}
      </Section>

      <Section label="Threads" count={tree.threads.length}>
        {tree.threads.map(t => (
          <Row key={t.name} depth={1} selected={sel({ kind: 'thread', name: t.name })}
            onClick={() => onSelect({ kind: 'thread', name: t.name })} title={t.thread_type}>
            <Dot tone={t.status === 'resolved' ? 'done' : t.status === 'abandoned' ? 'pending' : 'warn'} />
            <span className="truncate">{t.name}</span>
          </Row>
        ))}
      </Section>
    </div>
  )
}
