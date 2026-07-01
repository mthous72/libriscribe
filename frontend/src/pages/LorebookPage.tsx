import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
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
} from '../api/client'
import { useBrainstormStore } from '../store/brainstormSlice'
import LoreProposalReview, { Proposal } from '../components/LoreProposalReview'
import { Plus, Trash2, Search, Sparkles, Check, X, Edit3, AlertTriangle, Loader2, ChevronDown, ChevronRight, Upload } from 'lucide-react'

const TAB_TO_FOCUS: Record<string, string> = { Characters: 'character', Locations: 'location', Lore: 'lore', Arcs: 'arc' }
import { useUiStore } from '../store/uiSlice'

const TABS = ['Characters', 'Locations', 'Lore', 'Arcs', 'Threads', 'World', 'Graph']

function EntityList({ items, onSelect, onDelete, onAnalyze, labelKey = 'name', badgeKey }: any) {
  return (
    <div className="space-y-1">
      {items.map((item: any, i: number) => (
        <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 cursor-pointer" onClick={() => onSelect(item)}>
          <div>
            <span className="text-sm">{item[labelKey]}</span>
            {badgeKey && item[badgeKey] && <span className="ml-2 text-xs px-1.5 py-0.5 bg-gray-700 rounded">{item[badgeKey]}</span>}
          </div>
          <div className="flex gap-1">
            {onAnalyze && <button onClick={e => { e.stopPropagation(); onAnalyze(item) }} className="text-gray-600 hover:text-amber-400" title="Analyze"><Sparkles size={14} /></button>}
            <button onClick={e => { e.stopPropagation(); onDelete(item) }} className="text-gray-600 hover:text-red-400"><Trash2 size={14} /></button>
          </div>
        </div>
      ))}
      {items.length === 0 && <p className="text-gray-500 text-sm py-4 text-center">No entries yet</p>}
    </div>
  )
}

function FieldEditor({ fields, data, onChange }: { fields: string[], data: any, onChange: (key: string, val: any) => void }) {
  return (
    <div className="space-y-3">
      {fields.map(f => (
        <label key={f} className="block">
          <span className="text-xs text-gray-400 capitalize">{f.replace(/_/g, ' ')}</span>
          {typeof data[f] === 'object' && !Array.isArray(data[f]) ? (
            <textarea className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-20" value={JSON.stringify(data[f], null, 2)} onChange={e => { try { onChange(f, JSON.parse(e.target.value)); useUiStore.getState().markDirty() } catch {} }} />
          ) : Array.isArray(data[f]) ? (
            <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={data[f].join(', ')} onChange={e => { onChange(f, e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean)); useUiStore.getState().markDirty() }} />
          ) : (
            <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={data[f] ?? ''} onChange={e => { onChange(f, e.target.value); useUiStore.getState().markDirty() }} />
          )}
        </label>
      ))}
    </div>
  )
}

export default function LorebookPage() {
  const { name } = useParams<{ name: string }>()
  const [tab, setTab] = useState('Characters')
  const [characters, setCharacters] = useState<any[]>([])
  const [locations, setLocations] = useState<any[]>([])
  const [lore, setLore] = useState<any[]>([])
  const [arcs, setArcs] = useState<any[]>([])
  const [threads, setThreads] = useState<any[]>([])
  const [world, setWorld] = useState<any>({})
  const [xrefData, setXrefData] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
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
  }

  useEffect(() => { reload() }, [name])

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

  const charFields = ['name', 'age', 'role', 'physical_description', 'personality_traits', 'background', 'motivations', 'internal_conflicts', 'external_conflicts', 'character_arc']
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
      reload()
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
      if (tab === 'Locations') await deleteLocation(name, item.name)
      if (tab === 'Lore') await deleteLoreEntry(name, item.name)
      if (tab === 'Arcs') await deleteArc(name, item.name)
      if (tab === 'Threads') await deleteThread(name, item.name)
      setSelected(null)
      reload()
    } catch {}
  }

  const worldFields = Object.keys(world).filter(k => typeof world[k] === 'string')

  return (
    <div>
      {importProposal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-start justify-center overflow-y-auto p-4" onClick={() => setImportProposal(null)}>
          <div className="bg-gray-950 border border-gray-800 rounded-lg shadow-2xl w-full max-w-2xl mt-10 p-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-sm font-semibold">Review import</h2>
                {importFormat && <p className="text-[11px] text-gray-500">Detected: {importFormat}</p>}
              </div>
              <button onClick={() => setImportProposal(null)} className="text-gray-500 hover:text-gray-200"><X size={18} /></button>
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
      <h1 className="text-2xl font-bold mb-4">Lorebook</h1>
      <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
        <div className="flex gap-1">
          {TABS.map(t => (
            <button key={t} onClick={() => { setTab(t); setSelected(null) }} className={`px-3 py-1.5 rounded-lg text-sm ${tab === t ? 'bg-indigo-600' : 'bg-gray-800 hover:bg-gray-700'}`}>{t}</button>
          ))}
        </div>
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
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* List */}
        <div className="col-span-1 space-y-2">
          <button onClick={handleCreate} className="w-full flex items-center justify-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm"><Plus size={14} /> Add</button>
          {tab === 'Characters' && <EntityList items={characters} onSelect={(c: any) => { setSelected({ ...c, _origName: c.name }); setShowSuggestions(false) }} onDelete={handleDelete} onAnalyze={handleAnalyze} badgeKey="role" />}
          {tab === 'Locations' && <EntityList items={locations} onSelect={(l: any) => { setSelected({ ...l, _origName: l.name }); setShowSuggestions(false) }} onDelete={handleDelete} onAnalyze={handleAnalyze} />}
          {tab === 'Lore' && <EntityList items={lore} onSelect={(l: any) => { setSelected({ ...l, _origName: l.name }); setShowSuggestions(false) }} onDelete={handleDelete} onAnalyze={handleAnalyze} badgeKey="entry_type" />}
          {tab === 'Arcs' && <EntityList items={arcs} onSelect={(a: any) => { setSelected({ ...a, _origName: a.name }); setShowSuggestions(false) }} onDelete={handleDelete} badgeKey="status" />}
          {tab === 'Threads' && (
            <div className="space-y-1">
              {threads.map((t: any, i: number) => {
                const color = t.status === 'resolved' ? 'text-green-400' : t.status === 'abandoned' ? 'text-red-400' : 'text-yellow-400'
                return (
                  <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 cursor-pointer" onClick={() => setSelected({ ...t, _origName: t.name })}>
                    <div>
                      <span className={`text-sm ${color}`}>{t.name}</span>
                      <span className="ml-2 text-xs px-1.5 py-0.5 bg-gray-700 rounded">{t.thread_type}</span>
                      {t.opened_chapter && <span className="ml-1 text-xs text-gray-500">Ch.{t.opened_chapter}</span>}
                    </div>
                    <div className="flex gap-1">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${t.status === 'resolved' ? 'bg-green-900 text-green-300' : t.status === 'abandoned' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}>{t.status}</span>
                      <button onClick={e => { e.stopPropagation(); handleDelete(t) }} className="text-gray-600 hover:text-red-400"><Trash2 size={14} /></button>
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
            </div>
          )}
          {tab === 'World' && (
            <div className="text-xs text-gray-500">Edit worldbuilding fields on the right.</div>
          )}
        </div>

        {/* Detail / Editor */}
        <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-4">
          {tab === 'Characters' && selected && (
            <div>
              <FieldEditor fields={charFields} data={selected} onChange={(k, v) => setSelected({ ...selected, [k]: v })} />
              {/* Voice Profile (F3) */}
              <details className="mt-4 border border-gray-700 rounded-lg">
                <summary className="px-3 py-2 text-sm font-medium text-gray-300 cursor-pointer hover:bg-gray-800 rounded-t-lg flex items-center gap-1">
                  Voice Profile
                </summary>
                <div className="px-3 py-2 space-y-2 bg-gray-800/50">
                  {['speech_patterns', 'vocabulary_level', 'verbal_tics', 'avoids'].map(f => (
                    <label key={f} className="block">
                      <span className="text-xs text-gray-400 capitalize">{f.replace(/_/g, ' ')}</span>
                      <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={selected.voice_profile?.[f] || ''} onChange={e => setSelected({ ...selected, voice_profile: { ...selected.voice_profile, [f]: e.target.value } })} />
                    </label>
                  ))}
                  <label className="block">
                    <span className="text-xs text-gray-400">Example Dialogue (comma-separated)</span>
                    <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm" value={(selected.voice_profile?.example_dialogue || []).join(', ')} onChange={e => setSelected({ ...selected, voice_profile: { ...selected.voice_profile, example_dialogue: e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean) } })} />
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
              <FieldEditor fields={locFields} data={selected} onChange={(k, v) => setSelected({ ...selected, [k]: v })} />
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
              <FieldEditor fields={loreFields} data={selected} onChange={(k, v) => setSelected({ ...selected, [k]: v })} />
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
              <FieldEditor fields={arcFields} data={selected} onChange={(k, v) => setSelected({ ...selected, [k]: v })} />
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
              <FieldEditor fields={threadFields} data={selected} onChange={(k, v) => setSelected({ ...selected, [k]: v })} />
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
              <button onClick={() => name && updateWorldbuilding(name, world).then(() => { useUiStore.getState().markClean(); reload() })} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save Worldbuilding</button>
            </div>
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
                    <div className="flex gap-1.5 mt-1">
                      <button onClick={() => handleAccept(s.index)} className="flex items-center gap-0.5 px-2 py-0.5 bg-green-700 hover:bg-green-600 rounded text-xs"><Check size={12} /> Accept</button>
                      {editingIdx === s.index ? (
                        <button onClick={() => handleEditSuggestion(s.index)} className="flex items-center gap-0.5 px-2 py-0.5 bg-indigo-600 hover:bg-indigo-500 rounded text-xs"><Check size={12} /> Save</button>
                      ) : (
                        <button onClick={() => { setEditingIdx(s.index); setEditValue(s.proposed_value) }} className="flex items-center gap-0.5 px-2 py-0.5 bg-gray-600 hover:bg-gray-500 rounded text-xs"><Edit3 size={12} /> Edit</button>
                      )}
                      <button onClick={() => handleReject(s.index)} className="flex items-center gap-0.5 px-2 py-0.5 bg-red-700 hover:bg-red-600 rounded text-xs"><X size={12} /> Reject</button>
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
              <div className="flex gap-2">
                <input
                  className="flex-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
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
