import { useEffect, useRef, useState, useId } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import {
  listCharacters, createCharacter, updateCharacter, deleteCharacter,
  listLocations, createLocation, updateLocation, deleteLocation,
  listLoreEntries, createLoreEntry, updateLoreEntry, deleteLoreEntry,
  listArcs, createArc, updateArc, deleteArc,
  getWorldbuilding, updateWorldbuilding,
  listXref, searchProject,
  analyzeCharacter, analyzeLocation, analyzeLoreEntry, checkContinuity,
  listSuggestions, acceptSuggestion, rejectSuggestion, editSuggestion,
  listContinuityNotes,
  listThreads, createThread, updateThread, deleteThread,
  parseLore,
  listReferences, uploadReference, deleteReference,
  getGaps, deepScanGaps, getLastDeepScan, getProject, getConnections, getConnectionSuggestions,
  listSandboxRuns, getSandboxRun, deleteSandboxRun, patchSandboxCandidate, applySandboxRun, stageGapsToSandbox,
  extractCharacterStates, getTimeline,
} from '../api/client'
import { useBrainstormStore } from '../store/brainstormSlice'
import LoreProposalReview, { Proposal } from '../components/LoreProposalReview'
import { Plus, Trash2, Search, Sparkles, Check, X, Edit3, AlertTriangle, Loader2, ChevronDown, ChevronRight, Upload, RefreshCw } from 'lucide-react'

const TAB_TO_FOCUS: Record<string, string> = { Characters: 'character', Locations: 'location', Lore: 'lore', Arcs: 'arc', World: 'world' }
import { useUiStore } from '../store/uiSlice'

const TABS = ['Characters', 'Locations', 'Lore', 'Arcs', 'Threads', 'World', 'Graph', 'References', 'Gaps', 'Sandbox']
// Display labels (the internal tab key stays 'Lore' so routing/backend keys are unchanged).
const TAB_LABELS: Record<string, string> = { Lore: 'Codex' }

function EntityList({ items, onSelect, onDelete, onAnalyze, labelKey = 'name', badgeKey }: any) {
  return (
    <div className="space-y-1">
      {items.map((item: any, i: number) => (
        <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 cursor-pointer" onClick={() => onSelect(item)}>
          <div>
            <span className="text-sm">{item[labelKey]}</span>
            {badgeKey && item[badgeKey] && <span className="ml-2 text-xs px-1.5 py-0.5 bg-gray-700 rounded">{item[badgeKey]}</span>}
          </div>
          <div className="flex gap-0.5 -mr-1">
            {onAnalyze && <button onClick={e => { e.stopPropagation(); onAnalyze(item) }} className="text-gray-600 hover:text-amber-400 p-2" title="Analyze"><Sparkles size={14} /></button>}
            <button onClick={e => { e.stopPropagation(); onDelete(item) }} className="text-gray-600 hover:text-red-400 p-2" title="Delete"><Trash2 size={14} /></button>
          </div>
        </div>
      ))}
      {items.length === 0 && <p className="text-gray-500 text-sm py-4 text-center">No entries yet</p>}
    </div>
  )
}

// List fields (tags, chapters involved, example dialogue): edit as free text, parse ONLY on
// blur/Enter. Parsing per keystroke ate the separator the user just typed, making it impossible
// to enter more than one item.
function ListInput({ value, numeric = false, onCommit }: { value: any[], numeric?: boolean, onCommit: (v: any[]) => void }) {
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
const CHAPTER_FIELDS = new Set(['first_appearance', 'opened_chapter', 'target_resolution_chapter', 'resolved_chapter'])
// Entity-reference LIST fields → what records are valid targets ('characters' | 'all').
const ENTITY_LINK_FIELDS: Record<string, 'characters' | 'all'> = {
  associated_characters: 'characters', characters_involved: 'characters', related_entities: 'all',
}
// Each type's primary outgoing-link field — where auto-suggestions are offered.
const PRIMARY_LINK_FIELD: Record<string, string> = {
  character: 'relationships', location: 'associated_characters', lore: 'related_entities',
  arc: 'characters_involved', thread: 'characters_involved',
}
const dedupeAdd = (arr: string[], v: string) =>
  arr.some(x => x.toLowerCase() === v.trim().toLowerCase()) ? arr : [...arr, v.trim()]

// Chips + datalist input for a list of record names (validated options, but free-form allowed).
function TokenPicker({ value, options, suggestions = [], onChange }: { value: string[], options: string[], suggestions?: string[], onChange: (v: string[]) => void }) {
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
function RelationshipsEditor({ value, options, suggestions = [], onChange }: { value: Record<string, string>, options: string[], suggestions?: string[], onChange: (v: Record<string, string>) => void }) {
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

function FieldEditor({ fields, data, onChange, numChapters = 0, entityType = '', characterNames = [], allEntityNames = [], suggestions = [] }: { fields: string[], data: any, onChange: (key: string, val: any) => void, numChapters?: number, entityType?: string, characterNames?: string[], allEntityNames?: string[], suggestions?: { type: string, name: string }[] }) {
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
          ) : typeof data[f] === 'object' && !Array.isArray(data[f]) ? (
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

const TYPE_FOR_TAB: Record<string, string> = { Characters: 'character', Locations: 'location', Lore: 'lore', Arcs: 'arc', Threads: 'thread' }

// B25: navigable, bidirectional links for the selected entity. Resolved links jump to the record;
// unresolved names (no matching record) show as non-navigable "unlinked" chips.
function ConnectionsPanel({ projectName, entityType, entityName, version, onOpen }: { projectName: string, entityType: string, entityName: string, version: number, onOpen: (t: { type: string, name: string }) => void }) {
  const [conn, setConn] = useState<{ outgoing: any[], incoming: any[] } | null>(null)
  useEffect(() => {
    let cancelled = false
    getConnections(projectName, entityType, entityName)
      .then(c => { if (!cancelled) setConn(c) })
      .catch(() => { if (!cancelled) setConn({ outgoing: [], incoming: [] }) })
    return () => { cancelled = true }
  }, [projectName, entityType, entityName, version])

  if (!conn) return null
  if (!conn.outgoing.length && !conn.incoming.length) {
    return <div className="mt-4 border-t border-gray-800 pt-3 text-[11px] text-gray-600">No connections yet — add names to the relationship / involved / related / associated fields.</div>
  }
  const chip = (l: any, i: number, navigable: boolean) => {
    const body = <><span className="capitalize text-gray-500">{l.type || '?'}</span> <span className="text-gray-200">{l.name}</span><span className="text-gray-600"> · {l.relation}</span>{l.detail ? <span className="text-gray-600"> ({l.detail})</span> : null}</>
    return navigable
      ? <button key={i} onClick={() => onOpen({ type: l.type, name: l.name })} className="px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs text-left">{body}</button>
      : <span key={i} title="Not in the lorebook yet" className="px-2 py-1 bg-gray-800/40 rounded text-xs text-gray-500">{l.name} <span className="text-[10px]">(unlinked)</span></span>
  }
  return (
    <div className="mt-4 border-t border-gray-800 pt-3 space-y-2">
      <h4 className="text-xs uppercase tracking-wide text-gray-500">Connections</h4>
      {conn.outgoing.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-gray-500">Links to:</span>
          {conn.outgoing.map((l, i) => chip(l, i, l.resolved))}
        </div>
      )}
      {conn.incoming.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-gray-500">Referenced by:</span>
          {conn.incoming.map((l, i) => chip(l, 1000 + i, true))}
        </div>
      )}
    </div>
  )
}

// B27 Slice A: per-run staged candidates with human cherry-pick. Nothing merges until the
// author accepts candidates and clicks Apply.
function SandboxPanel({ projectName, onApplied }: { projectName: string, onApplied: () => void }) {
  const [runs, setRuns] = useState<any[]>([])
  const [run, setRun] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [info, setInfo] = useState('')

  const refreshRuns = () => listSandboxRuns(projectName).then(setRuns).catch(() => setRuns([]))
  useEffect(() => { refreshRuns() }, [projectName])

  const openRun = (id: string) => getSandboxRun(projectName, id).then(setRun).catch(() => {})
  const setStatus = async (cid: string, status: string) => {
    try {
      await patchSandboxCandidate(projectName, run.id, cid, { status })
      setRun({ ...run, candidates: run.candidates.map((c: any) => c.id === cid ? { ...c, status } : c) })
    } catch {}
  }
  const rename = async (cid: string, newName: string) => {
    try {
      await patchSandboxCandidate(projectName, run.id, cid, { name: newName })
      setRun({ ...run, candidates: run.candidates.map((c: any) => c.id === cid ? { ...c, name: newName } : c) })
    } catch {}
  }
  const applyRun = async () => {
    const n = run.candidates.filter((c: any) => c.status === 'accepted').length
    if (!n) { setInfo('Accept at least one candidate first.'); return }
    if (!confirm(`Merge ${n} accepted candidate${n === 1 ? '' : 's'} into the lorebook?`)) return
    setBusy(true)
    try {
      const r = await applySandboxRun(projectName, run.id)
      setInfo(`Applied ${r.applied} candidate${r.applied === 1 ? '' : 's'}.`)
      setRun(null); refreshRuns(); onApplied()
    } catch (e: any) { setInfo(e?.response?.data?.detail || 'Apply failed') }
    finally { setBusy(false) }
  }
  const removeRun = async (id: string) => {
    if (!confirm('Delete this run and its staged candidates?')) return
    try { await deleteSandboxRun(projectName, id); if (run?.id === id) setRun(null); refreshRuns() } catch {}
  }

  const SEED_LABEL: Record<string, string> = { gap_scan: 'Gap scan', manual: 'Manual', wizard: 'Story wizard' }
  const statusCls: Record<string, string> = { accepted: 'border-green-700 bg-green-900/20', rejected: 'border-red-900 bg-red-950/20 opacity-60', pending: 'border-gray-700 bg-gray-800/50' }

  if (run) {
    const cats = ['characters', 'locations', 'lore', 'arcs']
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <button onClick={() => setRun(null)} className="text-xs text-gray-400 hover:text-gray-200">← All runs</button>
          <div className="flex gap-2">
            <button onClick={applyRun} disabled={busy || run.status === 'applied'} className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded text-xs font-medium disabled:opacity-50">
              {busy ? 'Applying…' : run.status === 'applied' ? 'Applied' : 'Apply accepted'}
            </button>
            <button onClick={() => removeRun(run.id)} className="px-3 py-1.5 bg-gray-800 hover:bg-red-900 rounded text-xs">Delete run</button>
          </div>
        </div>
        {info && <div className="text-[11px] text-gray-400">{info}</div>}
        {cats.map(cat => {
          const group = run.candidates.filter((c: any) => c.category === cat)
          if (!group.length) return null
          return (
            <div key={cat}>
              <h3 className="text-xs uppercase tracking-wide text-gray-500 mb-1.5">{cat === 'lore' ? 'Codex' : cat} ({group.length})</h3>
              <div className="space-y-1.5">
                {group.map((c: any) => (
                  <div key={c.id} className={`border rounded-lg px-3 py-2 ${statusCls[c.status] || statusCls.pending}`}>
                    <div className="flex items-center gap-2">
                      <input value={c.name} onChange={e => rename(c.id, e.target.value)}
                        className="flex-1 bg-transparent border-b border-transparent focus:border-gray-600 text-sm font-medium outline-none" />
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${c.op === 'new' ? 'bg-green-900/60 text-green-300' : 'bg-blue-900/60 text-blue-300'}`}>{c.op}</span>
                      <button onClick={() => setStatus(c.id, c.status === 'accepted' ? 'pending' : 'accepted')} title="Accept"
                        className={`p-1.5 rounded ${c.status === 'accepted' ? 'bg-green-700 text-white' : 'bg-gray-700 text-gray-300 hover:bg-green-800'}`}><Check size={13} /></button>
                      <button onClick={() => setStatus(c.id, c.status === 'rejected' ? 'pending' : 'rejected')} title="Reject"
                        className={`p-1.5 rounded ${c.status === 'rejected' ? 'bg-red-800 text-white' : 'bg-gray-700 text-gray-300 hover:bg-red-900'}`}><X size={13} /></button>
                    </div>
                    {c.rationale && <div className="text-xs text-gray-400 mt-1">{c.rationale}</div>}
                    {c.evidence && <div className="text-[11px] text-gray-600">{c.evidence}</div>}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500">Staged candidates from gap scans (and, later, auto-explore and the story wizard). Nothing merges into the lorebook until you accept it and apply the run.</p>
      {runs.map(r => (
        <div key={r.id} className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 cursor-pointer" onClick={() => openRun(r.id)}>
          <div>
            <span className="text-sm">{SEED_LABEL[r.seed?.kind] || r.seed?.kind || 'Run'} · {new Date(r.created_at).toLocaleString()}</span>
            <span className="block text-[11px] text-gray-500">
              {r.candidate_count} candidate{r.candidate_count === 1 ? '' : 's'} — {r.counts?.accepted || 0} accepted · {r.counts?.rejected || 0} rejected · {r.counts?.pending || 0} pending
              {r.status === 'applied' && <span className="text-green-500"> · applied</span>}
            </span>
          </div>
          <button onClick={e => { e.stopPropagation(); removeRun(r.id) }} className="text-gray-600 hover:text-red-400 p-2"><Trash2 size={14} /></button>
        </div>
      ))}
      {runs.length === 0 && <p className="text-gray-500 text-sm py-6 text-center">No sandbox runs yet. Run a Deep scan on the Gaps tab and stage the results.</p>}
    </div>
  )
}

export default function LorebookPage() {
  const { name } = useParams<{ name: string }>()
  // Deep-link: navigate(..., { state: { tab: 'Sandbox' } }) opens that tab (the wizard uses it).
  const location = useLocation()
  const initialTab = (location.state as any)?.tab
  const [tab, setTab] = useState(TABS.includes(initialTab) ? initialTab : 'Characters')
  const [characters, setCharacters] = useState<any[]>([])
  const [locations, setLocations] = useState<any[]>([])
  const [lore, setLore] = useState<any[]>([])
  const [arcs, setArcs] = useState<any[]>([])
  const [threads, setThreads] = useState<any[]>([])
  const [world, setWorld] = useState<any>({})
  const [xrefData, setXrefData] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  // Per-RECORD unsaved-edit tracking: the re-sync guard used the GLOBAL dirty flag, so having
  // touched anything anywhere silently blocked brainstorm-apply refreshes of the open record.
  const selectedDirtyRef = useRef(false)
  const [staleFresh, setStaleFresh] = useState<any>(null)  // newer server copy held back by unsaved edits
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [continuityNotes, setContinuityNotes] = useState<any[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [editingIdx, setEditingIdx] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')
  const [smartImport, setSmartImport] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importProposal, setImportProposal] = useState<Proposal | null>(null)
  const [importFormat, setImportFormat] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const openBrainstorm = useBrainstormStore(s => s.openBrainstorm)
  // Refresh when lore is written elsewhere (e.g. brainstorm Apply-to-lore, which is a separate component).
  const loreVersion = useBrainstormStore(s => s.loreVersion)
  const bumpLore = useBrainstormStore(s => s.bumpLore)
  const lastLoreVersion = useRef(loreVersion)
  const [numChapters, setNumChapters] = useState(0)
  useEffect(() => {
    if (!name) return
    getProject(name).then((p: any) => {
      const nc = p?.num_chapters
      setNumChapters(Array.isArray(nc) ? (nc.length ? Math.max(...nc.map(Number)) : 0) : (Number(nc) || 0))
    }).catch(() => {})
  }, [name])
  // B25: record-name lists for the link pickers + co-occurrence suggestions for the selected entity.
  const characterNames = characters.map((c: any) => c.name).filter(Boolean)
  const allEntityNames = [...characters, ...locations, ...lore, ...arcs, ...threads].map((e: any) => e.name).filter(Boolean)
  const [linkSuggestions, setLinkSuggestions] = useState<{ type: string, name: string }[]>([])
  useEffect(() => {
    const et = TYPE_FOR_TAB[tab]
    if (!name || !selected?._origName || !et) { setLinkSuggestions([]); return }
    let cancelled = false
    getConnectionSuggestions(name, et, selected._origName)
      .then(r => { if (!cancelled) setLinkSuggestions(r.suggestions || []) })
      .catch(() => { if (!cancelled) setLinkSuggestions([]) })
    return () => { cancelled = true }
  }, [name, tab, selected?._origName, loreVersion])
  const [timelineEvents, setTimelineEvents] = useState<any[]>([])
  const [tlBusy, setTlBusy] = useState(false)
  useEffect(() => { if (tab === 'Graph' && name) getTimeline(name).then(setTimelineEvents).catch(() => {}) }, [tab, name])
  const [gaps, setGaps] = useState<{ gaps: any[], counts: any } | null>(null)
  const [gapsLoading, setGapsLoading] = useState(false)
  const [deepGaps, setDeepGaps] = useState<any[] | null>(null)
  const [deepScanning, setDeepScanning] = useState(false)
  const [deepInfo, setDeepInfo] = useState('')

  const loadGaps = async () => {
    if (!name) return
    setGapsLoading(true)
    try { setGaps(await getGaps(name)) } catch { setGaps({ gaps: [], counts: { total: 0 } }) }
    finally { setGapsLoading(false) }
  }
  const runDeepScan = async () => {
    if (!name) return
    setDeepScanning(true); setDeepInfo('')
    try {
      const r = await deepScanGaps(name)
      setDeepGaps(r.gaps || [])
      setDeepInfo(r.detail || `Scanned ${r.scanned} source${r.scanned === 1 ? '' : 's'}${r.truncated ? ' (top matches shown)' : ''}.`)
    } catch (e: any) {
      setDeepInfo(e?.response?.data?.detail || 'Deep scan failed.')
    } finally { setDeepScanning(false) }
  }
  // (Re)load the gap report when the tab opens or lore changes. The last deep scan is PERSISTED
  // server-side, so navigating away never wastes the multi-call scan — reload it here.
  useEffect(() => {
    if (tab !== 'Gaps' || !name) return
    loadGaps()
    getLastDeepScan(name).then(r => {
      if (r.gaps?.length) {
        setDeepGaps(r.gaps)
        setDeepInfo(r.scanned_at ? `Deep scan from ${new Date(r.scanned_at).toLocaleString()}${r.truncated ? ' (top matches shown)' : ''} — re-run after big lore changes.` : '')
      } else { setDeepGaps(null); setDeepInfo('') }
    }).catch(() => { setDeepGaps(null); setDeepInfo('') })
  }, [tab, name, loreVersion])

  const TAB_FOR_TYPE: Record<string, string> = { character: 'Characters', location: 'Locations', lore: 'Lore', arc: 'Arcs', thread: 'Threads' }
  const openEntity = (target: { type: string, name: string }) => {
    const t = TAB_FOR_TYPE[target.type]
    if (!t) return
    setTab(t)
    const listMap: Record<string, any[]> = { Characters: characters, Locations: locations, Lore: lore, Arcs: arcs, Threads: threads }
    const found = (listMap[t] || []).find(e => e.name === target.name)
    if (found) { selectedDirtyRef.current = false; setStaleFresh(null); setSelected({ ...found, _origName: found.name }) }
  }

  const onImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !name) return
    setImporting(true)
    try {
      const data = JSON.parse(await file.text())
      const r = await parseLore(name, { data, smart: smartImport })
      setImportProposal(r.proposal)
      setImportFormat(r.format + (r.used_llm && !String(r.format).includes('AI') ? ' (AI-mapped)' : ''))
    } catch (err: any) {
      if (err instanceof SyntaxError) alert('That file is not valid JSON.')
      else alert(err?.response?.data?.detail || 'Import failed')
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const reload = async () => {
    if (!name) return
    const [c, l, le, a, w, x, th] = await Promise.all([
      listCharacters(name).catch(() => []),
      listLocations(name).catch(() => []),
      listLoreEntries(name).catch(() => []),
      listArcs(name).catch(() => []),
      getWorldbuilding(name).catch(() => ({})),
      listXref(name).catch(() => []),
      listThreads(name).catch(() => []),
    ])
    setCharacters(c); setLocations(l); setLore(le); setArcs(a); setWorld(w); setXrefData(x); setThreads(th)
    // Re-sync the open detail pane with fresh server data so an in-place change (brainstorm
    // Apply-to-lore on the entity you're viewing, or our own Save) shows immediately without
    // switching tabs. Skip when the user has unsaved edits so we never clobber in-progress typing.
    setSelected((prev: any) => {
      if (!prev) return prev
      const listByTab: Record<string, any[]> = { Characters: c, Locations: l, Lore: le, Arcs: a, Threads: th }
      const list = listByTab[tab]
      if (!list) return prev
      const target = String(prev._origName || prev.name).toLowerCase()
      const fresh = list.find((e: any) => String(e.name).toLowerCase() === target)
      if (!fresh) return prev
      if (selectedDirtyRef.current) {
        // Don't clobber in-progress edits — but surface that a newer copy exists.
        const { _origName, ...cur } = prev
        if (JSON.stringify(cur) !== JSON.stringify(fresh)) setStaleFresh(fresh)
        return prev
      }
      setStaleFresh(null)
      return { ...fresh, _origName: fresh.name }
    })
  }

  useEffect(() => { reload() }, [name])

  // Reload when something else writes lore (brainstorm Apply-to-lore) — fires only on an actual bump.
  useEffect(() => {
    if (loreVersion === lastLoreVersion.current) return
    lastLoreVersion.current = loreVersion
    reload()
  }, [loreVersion])

  const doSearch = async () => {
    if (!name || !searchQuery) return
    const results = await searchProject(name, { query: searchQuery, top_k: 10 })
    setSearchResults(results)
  }

  const handleAnalyze = async (item: any) => {
    if (!name) return
    setAnalyzing(true)
    setShowSuggestions(true)
    try {
      let newSuggestions: any[] = []
      if (tab === 'Characters') newSuggestions = await analyzeCharacter(name, item.name)
      if (tab === 'Locations') newSuggestions = await analyzeLocation(name, item.name)
      if (tab === 'Lore') newSuggestions = await analyzeLoreEntry(name, item.name)
      setSuggestions(newSuggestions)
    } catch { setSuggestions([]) }
    setAnalyzing(false)
  }

  const handleContinuityCheck = async () => {
    if (!name) return
    setAnalyzing(true)
    try {
      const notes = await checkContinuity(name)
      setContinuityNotes(notes)
    } catch { setContinuityNotes([]) }
    setAnalyzing(false)
  }

  const handleAccept = async (idx: number) => {
    if (!name) return
    await acceptSuggestion(name, idx)
    setSuggestions(prev => prev.map(s => s.index === idx ? { ...s, status: 'accepted' } : s))
    reload()
  }

  const handleReject = async (idx: number) => {
    if (!name) return
    await rejectSuggestion(name, idx)
    setSuggestions(prev => prev.map(s => s.index === idx ? { ...s, status: 'rejected' } : s))
  }

  const handleEditSuggestion = async (idx: number) => {
    if (!name) return
    await editSuggestion(name, idx, { proposed_value: editValue })
    setSuggestions(prev => prev.map(s => s.index === idx ? { ...s, proposed_value: editValue } : s))
    setEditingIdx(null)
    setEditValue('')
  }

  const loadSuggestions = async () => {
    if (!name) return
    const s = await listSuggestions(name, 'all')
    setSuggestions(s)
    setShowSuggestions(true)
  }

  const threadFields = ['name', 'thread_type', 'description', 'opened_chapter', 'target_resolution_chapter', 'resolved_chapter', 'status', 'characters_involved']

  const charFields = ['name', 'age', 'sex', 'sexual_orientation', 'role', 'physical_description', 'personality_traits', 'background', 'motivations', 'internal_conflicts', 'external_conflicts', 'character_arc']
  const locFields = ['name', 'description', 'significance', 'associated_characters', 'first_appearance', 'tags']
  const loreFields = ['name', 'entry_type', 'description', 'significance', 'related_entities', 'first_appearance', 'tags']
  const arcFields = ['name', 'description', 'arc_type', 'chapters_involved', 'characters_involved', 'status', 'resolution_notes']

  const handleSave = async () => {
    if (!name || !selected) return
    const s = selected
    try {
      if (tab === 'Characters') await updateCharacter(name, s._origName || s.name, s)
      if (tab === 'Locations') await updateLocation(name, s._origName || s.name, s)
      if (tab === 'Lore') await updateLoreEntry(name, s._origName || s.name, s)
      if (tab === 'Arcs') await updateArc(name, s._origName || s.name, s)
      if (tab === 'Threads') await updateThread(name, s._origName || s.name, s)
      useUiStore.getState().markClean()
      selectedDirtyRef.current = false
      setStaleFresh(null)
      reload()
      bumpLore()  // refresh connections + any open views after link edits
    } catch (e) { alert('Save failed') }
  }

  const handleCreate = async () => {
    if (!name) return
    const newName = prompt('Name:')
    if (!newName) return
    try {
      if (tab === 'Characters') await createCharacter(name, { name: newName })
      if (tab === 'Locations') await createLocation(name, { name: newName })
      if (tab === 'Lore') await createLoreEntry(name, { name: newName })
      if (tab === 'Arcs') await createArc(name, { name: newName })
      if (tab === 'Threads') await createThread(name, { name: newName })
      reload()
    } catch {}
  }

  const handleDelete = async (item: any) => {
    if (!name || !confirm(`Delete "${item.name}"?`)) return
    try {
      if (tab === 'Characters') await deleteCharacter(name, item.name)
      else if (tab === 'Locations') await deleteLocation(name, item.name)
      else if (tab === 'Lore') await deleteLoreEntry(name, item.name)
      else if (tab === 'Arcs') await deleteArc(name, item.name)
      else if (tab === 'Threads') await deleteThread(name, item.name)
      setSelected(null)
      await reload()
    } catch (e: any) {
      // Surface the real reason instead of silently doing nothing.
      alert(`Couldn't delete "${item.name}": ${e?.response?.data?.detail || e?.message || 'request failed'}`)
    }
  }

  const worldFields = Object.keys(world).filter(k => typeof world[k] === 'string')

  return (
    <div>
      {importProposal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center overflow-y-auto p-4" onClick={() => setImportProposal(null)}>
          <div className="bg-gray-950 border border-gray-800 rounded-lg shadow-2xl w-full max-w-2xl max-h-[calc(100vh-2rem)] overflow-y-auto p-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-sm font-semibold">Review import</h2>
                {importFormat && <p className="text-[11px] text-gray-500">Detected: {importFormat}</p>}
              </div>
              <button onClick={() => setImportProposal(null)} className="text-gray-500 hover:text-gray-200 p-1.5 -m-1" title="Close"><X size={18} /></button>
            </div>
            <LoreProposalReview
              projectName={name!}
              proposal={importProposal}
              onApplied={() => reload()}
              onCancel={() => setImportProposal(null)}
            />
          </div>
        </div>
      )}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Lorebook</h1>
        <button onClick={() => reload()} title="Refresh from the project (e.g. after applying lore from a brainstorm)" className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>
      <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
        <div className="flex gap-1 flex-wrap">
          {TABS.map(t => (
            <button key={t} onClick={() => { setTab(t); setSelected(null) }} className={`px-3 py-1.5 rounded-lg text-sm ${tab === t ? 'bg-indigo-600' : 'bg-gray-800 hover:bg-gray-700'}`}>{TAB_LABELS[t] || t}</button>
          ))}
        </div>
        {tab !== 'References' && (
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400 flex items-center gap-1" title="Use the LLM to re-classify and enrich entries (helps with foreign formats). Recognized formats import without it.">
            <input type="checkbox" checked={smartImport} onChange={e => setSmartImport(e.target.checked)} /> AI-map
          </label>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            title="Import lore from JSON — our bundle, SillyTavern character cards, or KoboldAI / SillyTavern World Info. You'll review before anything is saved."
            className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm disabled:opacity-50"
          >
            {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Import JSON
          </button>
          <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={onImportFile} />
        </div>
        )}
      </div>

      {tab === 'References' && <ReferencesPanel name={name!} />}

      {tab === 'Sandbox' && <SandboxPanel projectName={name!} onApplied={() => { reload(); }} />}

      {tab === 'Gaps' && (() => {
        const allGaps = [...(gaps?.gaps || []), ...(deepGaps || [])]
        const LABELS: Record<string, string> = {
          dangling_reference: 'Dangling references', out_of_range_chapter: 'Chapters out of range',
          thin_character: 'Thin characters', unresolved_arc: 'Unresolved arcs',
          unresolved_thread: 'Open threads', missing_voice: 'Missing voice profiles',
          undefined_entity: 'Referenced but undefined (AI)',
        }
        const ORDER = ['dangling_reference', 'out_of_range_chapter', 'thin_character', 'undefined_entity', 'unresolved_arc', 'unresolved_thread', 'missing_voice'] as const
        return (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm text-gray-400">
              {gaps?.counts?.total ? (
                <span><span className="text-amber-400 font-medium">{gaps.counts.warn}</span> to fix · <span className="text-gray-400">{gaps.counts.info}</span> to consider</span>
              ) : 'Structural checks on your lore — no LLM.'}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button onClick={runDeepScan} disabled={deepScanning} title="Use the AI to scan prose + lore for names that have no record. Costs LLM calls; runs at your Max concurrent requests." className="flex items-center gap-1 px-2 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-xs disabled:opacity-50">
                {deepScanning ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Deep scan (uses AI)
              </button>
              <button onClick={loadGaps} disabled={gapsLoading} className="flex items-center gap-1 px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs disabled:opacity-50">
                {gapsLoading ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} Refresh
              </button>
              {allGaps.length > 0 && (
                <button onClick={async () => {
                  try {
                    const r = await stageGapsToSandbox(name!, allGaps)
                    setDeepInfo(`Staged ${r.candidates?.length ?? allGaps.length} candidates — review them in the Sandbox tab.`)
                    setTab('Sandbox')
                  } catch (e: any) { setDeepInfo(e?.response?.data?.detail || 'Staging failed') }
                }} title="Stage these findings as sandbox candidates you can accept/reject and merge"
                  className="flex items-center gap-1 px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs">
                  <Upload size={13} /> Stage into sandbox
                </button>
              )}
            </div>
          </div>
          {(deepScanning || deepInfo) && (
            <div className="text-[11px] text-gray-500 flex items-center gap-2">
              {deepScanning ? <><Loader2 size={12} className="animate-spin" /> AI is scanning prose &amp; lore for undefined names…</> : deepInfo}
            </div>
          )}
          {gapsLoading && !gaps ? (
            <div className="text-gray-500 text-sm flex items-center gap-2"><Loader2 size={15} className="animate-spin" /> Scanning…</div>
          ) : (allGaps.length === 0) ? (
            <div className="text-center text-gray-500 py-10">
              <Check size={28} className="mx-auto mb-2 text-green-500" />
              No structural gaps found. Try <span className="text-indigo-400">Deep scan</span> to hunt for referenced-but-undefined names.
            </div>
          ) : (
            ORDER.map(type => {
              const group = allGaps.filter(g => g.type === type)
              if (group.length === 0) return null
              return (
                <div key={type}>
                  <h3 className="text-xs uppercase tracking-wide text-gray-500 mb-1.5">{LABELS[type]} ({group.length})</h3>
                  <div className="space-y-1.5">
                    {group.map(g => {
                      const inner = (
                        <>
                          <span className={`mt-1 shrink-0 w-2 h-2 rounded-full ${g.severity === 'warn' ? 'bg-amber-400' : 'bg-gray-500'}`} />
                          <span className="min-w-0">
                            <span className="text-sm"><span className="font-medium">{g.entity_name}</span> <span className="text-gray-500 capitalize">· {g.entity_type}{g.target ? '' : ' (not in lorebook)'}</span></span>
                            <span className="block text-xs text-gray-400">{g.message}</span>
                            {g.evidence && <span className="block text-[11px] text-gray-600">{g.evidence}</span>}
                          </span>
                        </>
                      )
                      return g.target ? (
                        <button key={g.id} onClick={() => openEntity(g.target)} className="w-full text-left flex items-start gap-2 px-3 py-2 bg-gray-800/60 hover:bg-gray-700 rounded-lg">{inner}</button>
                      ) : (
                        <div key={g.id} className="flex items-start gap-2 px-3 py-2 bg-gray-800/40 rounded-lg">{inner}</div>
                      )
                    })}
                  </div>
                </div>
              )
            })
          )}
        </div>
        )
      })()}

      <div className={`grid grid-cols-1 lg:grid-cols-3 gap-4 ${(tab === 'References' || tab === 'Gaps' || tab === 'Sandbox') ? 'hidden' : ''}`}>
        {/* List */}
        <div className="lg:col-span-1 space-y-2">
          <button onClick={handleCreate} className="w-full flex items-center justify-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm"><Plus size={14} /> Add</button>
          {tab === 'Characters' && <EntityList items={characters} onSelect={(c: any) => { selectedDirtyRef.current = false; setStaleFresh(null); setSelected({ ...c, _origName: c.name }); setShowSuggestions(false) }} onDelete={handleDelete} onAnalyze={handleAnalyze} badgeKey="role" />}
          {tab === 'Locations' && <EntityList items={locations} onSelect={(l: any) => { selectedDirtyRef.current = false; setStaleFresh(null); setSelected({ ...l, _origName: l.name }); setShowSuggestions(false) }} onDelete={handleDelete} onAnalyze={handleAnalyze} />}
          {tab === 'Lore' && <EntityList items={lore} onSelect={(l: any) => { selectedDirtyRef.current = false; setStaleFresh(null); setSelected({ ...l, _origName: l.name }); setShowSuggestions(false) }} onDelete={handleDelete} onAnalyze={handleAnalyze} badgeKey="entry_type" />}
          {tab === 'Arcs' && <EntityList items={arcs} onSelect={(a: any) => { selectedDirtyRef.current = false; setStaleFresh(null); setSelected({ ...a, _origName: a.name }); setShowSuggestions(false) }} onDelete={handleDelete} badgeKey="status" />}
          {tab === 'Threads' && (
            <div className="space-y-1">
              {threads.map((t: any, i: number) => {
                const color = t.status === 'resolved' ? 'text-green-400' : t.status === 'abandoned' ? 'text-red-400' : 'text-yellow-400'
                return (
                  <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 cursor-pointer" onClick={() => { selectedDirtyRef.current = false; setStaleFresh(null); setSelected({ ...t, _origName: t.name }) }}>
                    <div>
                      <span className={`text-sm ${color}`}>{t.name}</span>
                      <span className="ml-2 text-xs px-1.5 py-0.5 bg-gray-700 rounded">{t.thread_type}</span>
                      {t.opened_chapter && <span className="ml-1 text-xs text-gray-500">Ch.{t.opened_chapter}</span>}
                    </div>
                    <div className="flex gap-1">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${t.status === 'resolved' ? 'bg-green-900 text-green-300' : t.status === 'abandoned' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}>{t.status}</span>
                      <button onClick={e => { e.stopPropagation(); handleDelete(t) }} className="text-gray-600 hover:text-red-400 p-2 -mr-1" title="Delete"><Trash2 size={14} /></button>
                    </div>
                  </div>
                )
              })}
              {threads.length === 0 && <p className="text-gray-500 text-sm py-4 text-center">No threads yet. Threads are auto-detected during chapter generation.</p>}
              {threads.filter((t: any) => t.status === 'open').length > 0 && (
                <div className="mt-2 px-3 py-2 bg-yellow-900/30 border border-yellow-800 rounded-lg text-xs text-yellow-300">
                  {threads.filter((t: any) => t.status === 'open').length} unresolved thread(s)
                </div>
              )}
            </div>
          )}
          {tab === 'Graph' && (
            <div className="space-y-2">
              {xrefData.map((e: any, i: number) => (
                <div key={i} className="bg-gray-800 rounded-lg p-2 text-xs">
                  <div className="font-medium">{e.entity_name} <span className="text-gray-500">({e.entity_type})</span></div>
                  {e.related_entities?.length > 0 && <div className="text-gray-400 mt-1">Related: {e.related_entities.join(', ')}</div>}
                  {e.referenced_in_chapters?.length > 0 && <div className="text-gray-500 mt-0.5">Ch: {e.referenced_in_chapters.join(', ')}</div>}
                </div>
              ))}
              {/* B33: lightweight story timeline (populated by Extract states) */}
              <div className="pt-2 border-t border-gray-800">
                <div className="flex items-center justify-between mb-1.5">
                  <h3 className="text-xs uppercase tracking-wide text-gray-500">Timeline</h3>
                  <button onClick={async () => {
                    setTlBusy(true)
                    try { await extractCharacterStates(name!); setTimelineEvents(await getTimeline(name!)) }
                    catch {} finally { setTlBusy(false) }
                  }} disabled={tlBusy} title="AI pass over written chapters: per-character states + key events (parallel)"
                    className="flex items-center gap-1 px-2 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-[11px] disabled:opacity-50">
                    {tlBusy ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />} Extract states (AI)
                  </button>
                </div>
                {timelineEvents.map((e: any, i: number) => (
                  <div key={i} className="text-xs text-gray-400 py-0.5">
                    <span className="text-gray-500">Ch {e.chapter_number}:</span> {e.description}
                    {e.characters_involved?.length > 0 && <span className="text-gray-600"> — {e.characters_involved.join(', ')}</span>}
                  </div>
                ))}
                {timelineEvents.length === 0 && <p className="text-[11px] text-gray-600">No timeline yet — click Extract states after writing chapters.</p>}
              </div>
            </div>
          )}
          {tab === 'World' && (
            <div className="text-xs text-gray-500">Edit worldbuilding fields on the right.</div>
          )}
        </div>

        {/* Detail / Editor */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-4">
          {staleFresh && selected && (
            <div className="mb-3 px-3 py-2 bg-amber-900/30 border border-amber-800 rounded-lg text-xs text-amber-200 flex items-center justify-between gap-2">
              <span>This record was updated elsewhere (e.g. a brainstorm apply) while you have unsaved edits.</span>
              <span className="flex gap-2 shrink-0">
                <button onClick={() => { setSelected({ ...staleFresh, _origName: staleFresh.name }); setStaleFresh(null); selectedDirtyRef.current = false }} className="px-2 py-1 bg-amber-700 hover:bg-amber-600 rounded">Load latest</button>
                <button onClick={() => setStaleFresh(null)} className="px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded">Keep my edits</button>
              </span>
            </div>
          )}
          {tab === 'Characters' && selected && (
            <div>
              <FieldEditor fields={charFields} data={selected} onChange={(k, v) => { selectedDirtyRef.current = true; setSelected({ ...selected, [k]: v }) }} entityType={TYPE_FOR_TAB[tab]} characterNames={characterNames} allEntityNames={allEntityNames} suggestions={linkSuggestions} />
              {/* Voice Profile (F3) */}
              <details className="mt-4 border border-gray-700 rounded-lg">
                <summary className="px-3 py-2 text-sm font-medium text-gray-300 cursor-pointer hover:bg-gray-800 rounded-t-lg flex items-center gap-1">
                  Voice Profile
                </summary>
                <div className="px-3 py-2 space-y-2 bg-gray-800/50">
                  {['speech_patterns', 'vocabulary_level', 'verbal_tics', 'avoids'].map(f => (
                    <label key={f} className="block">
                      <span className="text-xs text-gray-400 capitalize">{f.replace(/_/g, ' ')}</span>
                      <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={selected.voice_profile?.[f] || ''} onChange={e => { selectedDirtyRef.current = true; setSelected({ ...selected, voice_profile: { ...selected.voice_profile, [f]: e.target.value } }) }} />
                    </label>
                  ))}
                  <label className="block">
                    <span className="text-xs text-gray-400">Example Dialogue (comma-separated)</span>
                    <ListInput value={selected.voice_profile?.example_dialogue || []} onCommit={v => { selectedDirtyRef.current = true; setSelected({ ...selected, voice_profile: { ...selected.voice_profile, example_dialogue: v } }) }} />
                  </label>
                </div>
              </details>
              <div className="mt-4 flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save</button>
                {selected && TAB_TO_FOCUS[tab] && (
                  <button
                    onClick={() => openBrainstorm({ type: TAB_TO_FOCUS[tab], name: selected._origName || selected.name })}
                    title="Brainstorm this entry with the AI (uses surrounding lore as context)"
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1"
                  >
                    <Sparkles size={14} /> Brainstorm this
                  </button>
                )}
              </div>
            </div>
          )}
          {tab === 'Locations' && selected && (
            <div>
              <FieldEditor fields={locFields} data={selected} onChange={(k, v) => { selectedDirtyRef.current = true; setSelected({ ...selected, [k]: v }) }} numChapters={numChapters} entityType={TYPE_FOR_TAB[tab]} characterNames={characterNames} allEntityNames={allEntityNames} suggestions={linkSuggestions} />
              <div className="mt-4 flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save</button>
                {selected && TAB_TO_FOCUS[tab] && (
                  <button
                    onClick={() => openBrainstorm({ type: TAB_TO_FOCUS[tab], name: selected._origName || selected.name })}
                    title="Brainstorm this entry with the AI (uses surrounding lore as context)"
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1"
                  >
                    <Sparkles size={14} /> Brainstorm this
                  </button>
                )}
              </div>
            </div>
          )}
          {tab === 'Lore' && selected && (
            <div>
              <FieldEditor fields={loreFields} data={selected} onChange={(k, v) => { selectedDirtyRef.current = true; setSelected({ ...selected, [k]: v }) }} numChapters={numChapters} entityType={TYPE_FOR_TAB[tab]} characterNames={characterNames} allEntityNames={allEntityNames} suggestions={linkSuggestions} />
              <div className="mt-4 flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save</button>
                {selected && TAB_TO_FOCUS[tab] && (
                  <button
                    onClick={() => openBrainstorm({ type: TAB_TO_FOCUS[tab], name: selected._origName || selected.name })}
                    title="Brainstorm this entry with the AI (uses surrounding lore as context)"
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1"
                  >
                    <Sparkles size={14} /> Brainstorm this
                  </button>
                )}
              </div>
            </div>
          )}
          {tab === 'Arcs' && selected && (
            <div>
              <FieldEditor fields={arcFields} data={selected} onChange={(k, v) => { selectedDirtyRef.current = true; setSelected({ ...selected, [k]: v }) }} numChapters={numChapters} entityType={TYPE_FOR_TAB[tab]} characterNames={characterNames} allEntityNames={allEntityNames} suggestions={linkSuggestions} />
              {/* Milestones (F1) */}
              {selected.milestones && selected.milestones.length > 0 && (
                <div className="mt-4 border border-gray-700 rounded-lg p-3">
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Milestones</h4>
                  <div className="space-y-2">
                    {selected.milestones.map((m: any, i: number) => (
                      <div key={i} className="bg-gray-800 rounded p-2 text-xs">
                        <div className="flex justify-between">
                          <span className="font-medium">{m.name}</span>
                          <span className={`px-1.5 py-0.5 rounded ${m.status === 'completed' ? 'bg-green-900 text-green-300' : m.status === 'in_progress' ? 'bg-blue-900 text-blue-300' : 'bg-gray-700 text-gray-400'}`}>{m.status}</span>
                        </div>
                        <div className="text-gray-400 mt-1">{m.milestone_type} | Target: Ch.{m.target_chapter}{m.actual_chapter ? ` | Actual: Ch.${m.actual_chapter}` : ''}</div>
                        <p className="text-gray-500 mt-0.5">{m.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="mt-4 flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save</button>
                {selected && TAB_TO_FOCUS[tab] && (
                  <button
                    onClick={() => openBrainstorm({ type: TAB_TO_FOCUS[tab], name: selected._origName || selected.name })}
                    title="Brainstorm this entry with the AI (uses surrounding lore as context)"
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1"
                  >
                    <Sparkles size={14} /> Brainstorm this
                  </button>
                )}
              </div>
            </div>
          )}
          {tab === 'Threads' && selected && (
            <div>
              <FieldEditor fields={threadFields} data={selected} onChange={(k, v) => { selectedDirtyRef.current = true; setSelected({ ...selected, [k]: v }) }} numChapters={numChapters} entityType={TYPE_FOR_TAB[tab]} characterNames={characterNames} allEntityNames={allEntityNames} suggestions={linkSuggestions} />
              <div className="mt-4 flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save</button>
                {selected && TAB_TO_FOCUS[tab] && (
                  <button
                    onClick={() => openBrainstorm({ type: TAB_TO_FOCUS[tab], name: selected._origName || selected.name })}
                    title="Brainstorm this entry with the AI (uses surrounding lore as context)"
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1"
                  >
                    <Sparkles size={14} /> Brainstorm this
                  </button>
                )}
              </div>
            </div>
          )}
          {tab === 'World' && (
            <div className="space-y-3">
              {worldFields.map(f => (
                <label key={f} className="block">
                  <span className="text-xs text-gray-400 capitalize">{f.replace(/_/g, ' ')}</span>
                  <textarea
                    className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-16"
                    value={world[f] || ''}
                    onChange={e => { setWorld({ ...world, [f]: e.target.value }); useUiStore.getState().markDirty() }}
                  />
                </label>
              ))}
              <div className="flex gap-2">
                <button onClick={() => name && updateWorldbuilding(name, world).then(() => { useUiStore.getState().markClean(); reload() })} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save Worldbuilding</button>
                <button
                  onClick={() => openBrainstorm({ type: 'world', name: 'World' })}
                  title="Brainstorm the world with the AI (uses your lore as context); Apply routes into these worldbuilding fields"
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1"
                >
                  <Sparkles size={14} /> Brainstorm the world
                </button>
              </div>
            </div>
          )}
          {/* Connections (B25) — navigable links, both directions */}
          {selected && TYPE_FOR_TAB[tab] && (
            <ConnectionsPanel
              projectName={name!}
              entityType={TYPE_FOR_TAB[tab]}
              entityName={selected._origName || selected.name}
              version={loreVersion}
              onOpen={openEntity}
            />
          )}
          {/* Suggestion Review Panel */}
          {showSuggestions && (tab === 'Characters' || tab === 'Locations' || tab === 'Lore') && (
            <div className="mt-4 border-t border-gray-700 pt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium flex items-center gap-1">
                  <Sparkles size={14} className="text-amber-400" /> AI Suggestions
                </h3>
                <button onClick={() => setShowSuggestions(false)} className="text-xs text-gray-500 hover:text-gray-300">Hide</button>
              </div>
              {analyzing && (
                <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                  <Loader2 size={16} className="animate-spin" /> Analyzing...
                </div>
              )}
              {!analyzing && suggestions.length === 0 && (
                <p className="text-gray-500 text-xs py-2">No suggestions found. Try analyzing an entity.</p>
              )}
              {!analyzing && suggestions.map((s: any) => (
                <div key={s.index} className={`mb-3 p-3 rounded-lg text-xs ${s.status === 'accepted' ? 'bg-green-900/30 border border-green-800' : s.status === 'rejected' ? 'bg-red-900/30 border border-red-800 opacity-60' : 'bg-gray-800 border border-gray-700'}`}>
                  <div className="flex justify-between mb-1">
                    <span className="font-medium capitalize">{s.field.replace(/_/g, ' ')}</span>
                    <span className="text-gray-500">Ch. {s.source_chapter}</span>
                  </div>
                  {s.current_value && (
                    <div className="mb-1">
                      <span className="text-red-400">- </span>
                      <span className="text-gray-400">{s.current_value}</span>
                    </div>
                  )}
                  <div className="mb-1">
                    <span className="text-green-400">+ </span>
                    {editingIdx === s.index ? (
                      <input className="bg-gray-700 border border-gray-600 rounded px-1 py-0.5 text-xs w-3/4" value={editValue} onChange={e => setEditValue(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleEditSuggestion(s.index)} autoFocus />
                    ) : (
                      <span className="text-gray-200">{s.proposed_value}</span>
                    )}
                  </div>
                  {s.reason && <p className="text-gray-500 italic mb-2">{s.reason}</p>}
                  {s.status === 'pending' && (
                    <div className="flex gap-1.5 mt-1 flex-wrap">
                      <button onClick={() => handleAccept(s.index)} className="flex items-center gap-0.5 px-2 py-1 bg-green-700 hover:bg-green-600 rounded text-xs"><Check size={12} /> Accept</button>
                      {editingIdx === s.index ? (
                        <button onClick={() => handleEditSuggestion(s.index)} className="flex items-center gap-0.5 px-2 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-xs"><Check size={12} /> Save</button>
                      ) : (
                        <button onClick={() => { setEditingIdx(s.index); setEditValue(s.proposed_value) }} className="flex items-center gap-0.5 px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs"><Edit3 size={12} /> Edit</button>
                      )}
                      <button onClick={() => handleReject(s.index)} className="flex items-center gap-0.5 px-2 py-1 bg-red-700 hover:bg-red-600 rounded text-xs"><X size={12} /> Reject</button>
                    </div>
                  )}
                  {s.status !== 'pending' && (
                    <span className={`text-xs px-1.5 py-0.5 rounded ${s.status === 'accepted' ? 'bg-green-800 text-green-200' : 'bg-red-800 text-red-200'}`}>{s.status}</span>
                  )}
                </div>
              ))}
            </div>
          )}
          {tab === 'Graph' && (
            <div className="space-y-3">
              <div className="flex gap-2 flex-wrap">
                <input
                  className="flex-1 min-w-[10rem] px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
                  placeholder="Search across all content..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && doSearch()}
                />
                <button onClick={doSearch} className="px-3 py-1.5 bg-indigo-600 rounded text-sm"><Search size={14} /></button>
                <button onClick={handleContinuityCheck} disabled={analyzing} className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 rounded text-sm flex items-center gap-1 disabled:opacity-50">
                  {analyzing ? <Loader2 size={14} className="animate-spin" /> : <AlertTriangle size={14} />}
                  Continuity
                </button>
                <button onClick={loadSuggestions} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm flex items-center gap-1">
                  <Sparkles size={14} /> History
                </button>
              </div>
              {continuityNotes.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium flex items-center gap-1"><AlertTriangle size={14} className="text-amber-400" /> Continuity Issues</h3>
                  {continuityNotes.map((n: any, i: number) => (
                    <div key={i} className="bg-amber-900/20 border border-amber-800 rounded-lg p-3 text-xs">
                      <div className="flex justify-between mb-1">
                        <span className="font-medium text-amber-300">{n.note_type}</span>
                        {n.chapter_number > 0 && <span className="text-gray-500">Ch. {n.chapter_number}</span>}
                      </div>
                      <p className="text-gray-300">{n.description}</p>
                      {n.entities_involved?.length > 0 && <p className="text-gray-500 mt-1">Entities: {n.entities_involved.join(', ')}</p>}
                    </div>
                  ))}
                </div>
              )}
              {searchResults.map((r: any, i: number) => (
                <div key={i} className="bg-gray-800 rounded-lg p-3 text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="font-medium">{r.source_type}</span>
                    <span className="text-gray-500">Score: {r.score?.toFixed(3)}</span>
                  </div>
                  <p className="text-gray-300">{r.text?.slice(0, 200)}...</p>
                </div>
              ))}
            </div>
          )}
          {!selected && !showSuggestions && tab !== 'World' && tab !== 'Graph' && (
            <p className="text-gray-500 text-sm text-center py-10">Select an item to edit, or click <Sparkles size={14} className="inline text-amber-400" /> to analyze</p>
          )}
        </div>
      </div>
    </div>
  )
}

function ReferencesPanel({ name }: { name: string }) {
  const [refs, setRefs] = useState<any[]>([])
  const [ocrAvailable, setOcrAvailable] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const reload = async () => {
    try {
      const data = await listReferences(name)
      setRefs(data.references || [])
      setOcrAvailable(data.ocr_available !== false)
    } catch { /* ignore */ }
  }
  useEffect(() => { reload() }, [name])

  // Poll while any reference is still being processed (OCR can take a while).
  const processing = refs.some((r: any) => r.status === 'processing')
  useEffect(() => {
    if (!processing) return
    const t = setInterval(reload, 2000)
    return () => clearInterval(t)
  }, [processing, name])

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true); setError('')
    try {
      await uploadReference(name, file)
      await reload()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Upload failed')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const remove = async (id: string, title: string) => {
    if (!confirm(`Remove reference "${title}"?`)) return
    try { await deleteReference(name, id); await reload() } catch {}
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-medium text-gray-300">Reference material</h3>
          <p className="text-xs text-gray-500 max-w-xl mt-1">
            Import source documents (PDF, TXT, MD — and scanned PDFs or images via OCR) —
            research, a style guide, a series bible. LibriScribe grounds brainstorming and
            generation in these as <b>background source</b>, never as canon lore, and they're
            excluded from exports. Turning on Semantic/Hybrid search (project Dashboard) makes
            retrieval from them much stronger.
          </p>
          {!ocrAvailable && (
            <p className="text-[11px] text-amber-400/80 mt-1">
              OCR is unavailable (Tesseract not found) — text PDFs and text files still work, but
              scanned PDFs / images can't be read.
            </p>
          )}
        </div>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm disabled:opacity-50 whitespace-nowrap"
        >
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Add reference
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.txt,.md,.markdown,.text,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,application/pdf,text/plain,image/*" className="hidden" onChange={onFile} />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {refs.length === 0 ? (
        <p className="text-sm text-gray-500 py-6 text-center">No references yet. Add a PDF, text file, or scanned document to ground the AI in your source material.</p>
      ) : (
        <div className="space-y-1">
          {refs.map((r: any) => (
            <div key={r.id} className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg">
              <div className="min-w-0">
                <div className="text-sm truncate flex items-center gap-2">
                  {r.title || r.filename}
                  {r.ocr && <span className="text-[10px] px-1 py-0.5 bg-indigo-900/50 border border-indigo-800 rounded text-indigo-300">OCR</span>}
                </div>
                {r.status === 'processing' ? (
                  <div className="text-xs text-gray-400 flex items-center gap-1"><Loader2 size={11} className="animate-spin" /> Extracting &amp; indexing…</div>
                ) : r.status === 'error' ? (
                  <div className="text-xs text-red-400">Failed: {r.error || 'could not extract text'}</div>
                ) : (
                  <div className="text-xs text-gray-500">
                    {(r.char_count || 0).toLocaleString()} chars · {Math.max(1, Math.round((r.bytes || 0) / 1024))} KB
                  </div>
                )}
              </div>
              <button onClick={() => remove(r.id, r.title || r.filename)} className="text-gray-600 hover:text-red-400 p-2 -mr-1" title="Remove reference">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
