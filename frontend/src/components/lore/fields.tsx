import { useEffect, useState, useId } from 'react'
import { useUiStore } from '../../store/uiSlice'

// B45: the lore field-editing primitives, extracted from LorebookPage so the Story
// Workbench and the Lorebook page render the SAME editors (no behavior fork).

// Canonical per-type editable field lists (KB model order).
export const CHAR_FIELDS = ['name', 'age', 'sex', 'sexual_orientation', 'role', 'physical_description', 'personality_traits', 'background', 'motivations', 'internal_conflicts', 'external_conflicts', 'character_arc']
export const LOC_FIELDS = ['name', 'description', 'significance', 'associated_characters', 'first_appearance', 'tags']
export const LORE_FIELDS = ['name', 'entry_type', 'description', 'significance', 'related_entities', 'first_appearance', 'tags']
export const ARC_FIELDS = ['name', 'description', 'arc_type', 'chapters_involved', 'characters_involved', 'status', 'resolution_notes']
export const THREAD_FIELDS = ['name', 'thread_type', 'description', 'opened_chapter', 'target_resolution_chapter', 'resolved_chapter', 'status', 'characters_involved']

// List fields (tags, chapters involved, example dialogue): edit as free text, parse ONLY on
// blur/Enter. Parsing per keystroke ate the separator the user just typed, making it impossible
// to enter more than one item.
export function ListInput({ value, numeric = false, onCommit }: { value: any[], numeric?: boolean, onCommit: (v: any[]) => void }) {
  const [text, setText] = useState((value || []).join(', '))
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setText((value || []).join(', ')) }, [JSON.stringify(value || [])])  // eslint-disable-line react-hooks/exhaustive-deps
  const commit = () => {
    const parts = text.split(/[,;\n]/).map(p => p.trim()).filter(Boolean)
    onCommit(numeric ? parts.map(Number).filter(n => Number.isFinite(n)) : parts)
  }
  return (
    <input
      className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
      value={text}
      placeholder={numeric ? 'e.g. 1, 2, 5' : 'comma-separated'}
      onFocus={() => setFocused(true)}
      onChange={e => setText(e.target.value)}
      onBlur={() => { setFocused(false); commit() }}
      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); commit() } }}
    />
  )
}

// Single chapter-number fields — rendered as a chapter pulldown (they're ints, not free text).
export const CHAPTER_FIELDS = new Set(['first_appearance', 'opened_chapter', 'target_resolution_chapter', 'resolved_chapter'])
// Entity-reference LIST fields → what records are valid targets ('characters' | 'all').
export const ENTITY_LINK_FIELDS: Record<string, 'characters' | 'all'> = {
  associated_characters: 'characters', characters_involved: 'characters', related_entities: 'all',
}
// Each type's primary outgoing-link field — where auto-suggestions are offered.
export const PRIMARY_LINK_FIELD: Record<string, string> = {
  character: 'relationships', location: 'associated_characters', lore: 'related_entities',
  arc: 'characters_involved', thread: 'characters_involved',
}
const dedupeAdd = (arr: string[], v: string) =>
  arr.some(x => x.toLowerCase() === v.trim().toLowerCase()) ? arr : [...arr, v.trim()]

// Chips + datalist input for a list of record names (validated options, but free-form allowed).
export function TokenPicker({ value, options, suggestions = [], onChange }: { value: string[], options: string[], suggestions?: string[], onChange: (v: string[]) => void }) {
  const [text, setText] = useState('')
  const dlId = useId()
  const commit = (raw: string) => { const v = raw.trim(); if (v) onChange(dedupeAdd(value, v)); setText('') }
  const avail = options.filter(o => !value.some(v => v.toLowerCase() === o.toLowerCase()))
  const sugg = suggestions.filter(s => !value.some(v => v.toLowerCase() === s.toLowerCase()))
  return (
    <div className="mt-1">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-1">
          {value.map((v, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-900/40 border border-indigo-800 rounded text-xs">
              {v}<button onClick={() => onChange(value.filter((_, idx) => idx !== i))} className="text-indigo-300 hover:text-white">×</button>
            </span>
          ))}
        </div>
      )}
      <input list={dlId} value={text} placeholder="type a name, Enter to add…"
        onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commit(text) } }}
        className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" />
      <datalist id={dlId}>{avail.map(o => <option key={o} value={o} />)}</datalist>
      {sugg.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1 items-center">
          <span className="text-[10px] text-gray-500">Suggested:</span>
          {sugg.map(s => <button key={s} onClick={() => onChange(dedupeAdd(value, s))} className="px-1.5 py-0.5 bg-gray-800 hover:bg-gray-700 rounded text-[11px] text-gray-300">+ {s}</button>)}
        </div>
      )}
    </div>
  )
}

// Character relationships (name → description). Rename = remove + re-add (keeps it simple & controlled).
export function RelationshipsEditor({ value, options, suggestions = [], onChange }: { value: Record<string, string>, options: string[], suggestions?: string[], onChange: (v: Record<string, string>) => void }) {
  const [nn, setNn] = useState('')
  const [nd, setNd] = useState('')
  const dlId = useId()
  const v = value || {}
  const add = (name: string, desc = '') => { const k = name.trim(); if (!k) return; onChange({ ...v, [k]: desc }); setNn(''); setNd('') }
  const remove = (k: string) => { const next = { ...v }; delete next[k]; onChange(next) }
  const avail = options.filter(o => !(o.toLowerCase() in Object.fromEntries(Object.keys(v).map(k => [k.toLowerCase(), 1]))))
  const sugg = suggestions.filter(s => !Object.keys(v).some(k => k.toLowerCase() === s.toLowerCase()))
  return (
    <div className="mt-1 space-y-1.5">
      {Object.entries(v).map(([k, d]) => (
        <div key={k} className="flex items-center gap-1.5">
          <span className="px-2 py-0.5 bg-indigo-900/40 border border-indigo-800 rounded text-xs whitespace-nowrap">{k}</span>
          <input value={String(d)} placeholder="relationship…" onChange={e => onChange({ ...v, [k]: e.target.value })}
            className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" />
          <button onClick={() => remove(k)} className="text-gray-500 hover:text-red-400 text-sm px-1">×</button>
        </div>
      ))}
      <div className="flex items-center gap-1.5">
        <input list={dlId} value={nn} placeholder="add character…" onChange={e => setNn(e.target.value)}
          className="w-32 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" />
        <datalist id={dlId}>{avail.map(o => <option key={o} value={o} />)}</datalist>
        <input value={nd} placeholder="relationship (e.g. old ally)" onChange={e => setNd(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(nn, nd) } }}
          className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" />
        <button onClick={() => add(nn, nd)} className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs">Add</button>
      </div>
      {sugg.length > 0 && (
        <div className="flex flex-wrap gap-1 items-center">
          <span className="text-[10px] text-gray-500">Suggested:</span>
          {sugg.map(s => <button key={s} onClick={() => add(s)} className="px-1.5 py-0.5 bg-gray-800 hover:bg-gray-700 rounded text-[11px] text-gray-300">+ {s}</button>)}
        </div>
      )}
    </div>
  )
}

export function FieldEditor({ fields, data, onChange, numChapters = 0, entityType = '', characterNames = [], allEntityNames = [], suggestions = [] }: { fields: string[], data: any, onChange: (key: string, val: any) => void, numChapters?: number, entityType?: string, characterNames?: string[], allEntityNames?: string[], suggestions?: { type: string, name: string }[] }) {
  const dirty = <T,>(v: T) => { useUiStore.getState().markDirty(); return v }
  const suggestFor = (f: string, kind: 'characters' | 'all'): string[] => {
    if (f !== PRIMARY_LINK_FIELD[entityType]) return []
    return suggestions.filter(s => kind === 'all' || s.type === 'character').map(s => s.name)
  }
  return (
    <div className="space-y-3">
      {fields.map(f => (
        <label key={f} className="block">
          <span className="text-xs text-gray-400 capitalize">{f.replace(/_/g, ' ')}</span>
          {f === 'relationships' && entityType === 'character' ? (
            <RelationshipsEditor value={data[f] || {}} options={characterNames}
              suggestions={suggestFor('relationships', 'characters')}
              onChange={val => { onChange(f, val); useUiStore.getState().markDirty() }} />
          ) : ENTITY_LINK_FIELDS[f] ? (
            <TokenPicker value={Array.isArray(data[f]) ? data[f] : []}
              options={ENTITY_LINK_FIELDS[f] === 'characters' ? characterNames : allEntityNames}
              suggestions={suggestFor(f, ENTITY_LINK_FIELDS[f])}
              onChange={val => { onChange(f, val); useUiStore.getState().markDirty() }} />
          ) : CHAPTER_FIELDS.has(f) ? (
            numChapters >= 1 ? (
              <select className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
                value={data[f] ?? ''}
                onChange={e => { const v = e.target.value; onChange(f, v === '' ? null : Number(v)); useUiStore.getState().markDirty() }}>
                <option value="">— unset —</option>
                {Array.from({ length: numChapters }, (_, i) => i + 1).map(ch => <option key={ch} value={ch}>Chapter {ch}</option>)}
              </select>
            ) : (
              <input type="number" min={1} className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
                value={data[f] ?? ''}
                onChange={e => { const v = e.target.value; onChange(f, v === '' ? null : Number(v)); useUiStore.getState().markDirty() }} />
            )
          ) : typeof data[f] === 'object' && data[f] !== null && !Array.isArray(data[f]) ? (
            <textarea className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-20" value={JSON.stringify(data[f], null, 2)} onChange={e => { try { onChange(f, dirty(JSON.parse(e.target.value))) } catch {} }} />
          ) : Array.isArray(data[f]) ? (
            <ListInput value={data[f]} numeric={f === 'chapters_involved'} onCommit={v => { onChange(f, v); useUiStore.getState().markDirty() }} />
          ) : (
            <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={data[f] ?? ''} onChange={e => { onChange(f, e.target.value); useUiStore.getState().markDirty() }} />
          )}
        </label>
      ))}
    </div>
  )
}

// Character voice profile sub-editor (F3) — collapsed <details>, shared verbatim between
// the Lorebook page and the workbench CharacterEditor.
export function VoiceProfileEditor({ value, onChange }: { value: any, onChange: (vp: any) => void }) {
  const vp = value || {}
  return (
    <details className="mt-4 border border-gray-700 rounded-lg">
      <summary className="px-3 py-2 text-sm font-medium text-gray-300 cursor-pointer hover:bg-gray-800 rounded-t-lg flex items-center gap-1">
        Voice Profile
      </summary>
      <div className="px-3 py-2 space-y-2 bg-gray-800/50">
        {['speech_patterns', 'vocabulary_level', 'verbal_tics', 'avoids'].map(f => (
          <label key={f} className="block">
            <span className="text-xs text-gray-400 capitalize">{f.replace(/_/g, ' ')}</span>
            <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={vp[f] || ''} onChange={e => onChange({ ...vp, [f]: e.target.value })} />
          </label>
        ))}
        <label className="block">
          <span className="text-xs text-gray-400">Example Dialogue (comma-separated)</span>
          <ListInput value={vp.example_dialogue || []} onCommit={v => onChange({ ...vp, example_dialogue: v })} />
        </label>
      </div>
    </details>
  )
}
