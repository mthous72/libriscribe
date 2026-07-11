import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  parseChat, parseChatDebug, streamChat, previewChat,
  listCharacters, listLocations, listLoreEntries, listArcs,
  listSessions, createSession, updateSession, deleteSession, getSession, clearSession,
  listScenes, updateScene, updateChapterMeta, updateProjectMeta,
} from '../api/client'
import { useBrainstormStore } from '../store/brainstormSlice'
import { useWorkbenchStore } from '../store/workbenchSlice'
import LoreProposalReview, { Proposal } from './LoreProposalReview'
import { X, Send, Trash2, Loader2, Sparkles, Plus, Pencil, Eye, Save } from 'lucide-react'

interface Msg { role: string; content: string }

// Properties you can narrow a focused brainstorm to (per entity type). '' = the whole entity.
export const ASPECTS: Record<string, { value: string, label: string }[]> = {
  character: [
    { value: 'role', label: 'Role' },
    { value: 'age', label: 'Age' },
    { value: 'sex', label: 'Sex' },
    { value: 'sexual_orientation', label: 'Sexual orientation' },
    { value: 'physical_description', label: 'Physical description' },
    { value: 'personality_traits', label: 'Personality' },
    { value: 'background', label: 'Background' },
    { value: 'motivations', label: 'Motivations' },
    { value: 'internal_conflicts', label: 'Internal conflicts' },
    { value: 'external_conflicts', label: 'External conflicts' },
    { value: 'character_arc', label: 'Character arc' },
    { value: 'voice', label: 'Voice Profile' },
  ],
  location: [
    { value: 'description', label: 'Description' },
    { value: 'significance', label: 'Significance' },
    { value: 'associated_characters', label: 'Associated characters' },
    { value: 'first_appearance', label: 'First appearance' },
    { value: 'tags', label: 'Tags' },
  ],
  lore: [
    { value: 'entry_type', label: 'Type' },
    { value: 'description', label: 'Description' },
    { value: 'significance', label: 'Significance' },
    { value: 'related_entities', label: 'Related entities' },
    { value: 'first_appearance', label: 'First appearance' },
    { value: 'tags', label: 'Tags' },
  ],
  arc: [
    { value: 'arc_type', label: 'Arc type' },
    { value: 'description', label: 'Description' },
    { value: 'resolution_notes', label: 'Resolution notes' },
    { value: 'chapters_involved', label: 'Chapters involved' },
    { value: 'characters_involved', label: 'Characters involved' },
    { value: 'status', label: 'Status' },
  ],
  world: [
    { value: 'geography', label: 'Geography' },
    { value: 'culture_and_society', label: 'Culture & society' },
    { value: 'history', label: 'History' },
    { value: 'rules_and_laws', label: 'Rules & laws' },
    { value: 'technology_level', label: 'Technology level' },
    { value: 'magic_system', label: 'Magic system' },
    { value: 'key_locations', label: 'Key locations' },
    { value: 'important_organizations', label: 'Organizations' },
    { value: 'flora_and_fauna', label: 'Flora & fauna' },
    { value: 'languages', label: 'Languages' },
    { value: 'religions_and_beliefs', label: 'Religions & beliefs' },
    { value: 'economy', label: 'Economy' },
    { value: 'conflicts', label: 'Conflicts' },
  ],
  // B45: story-spine focus types (workbench focus-follow).
  concept: [
    { value: 'logline', label: 'Logline' },
    { value: 'description', label: 'Description' },
    { value: 'title', label: 'Title' },
    { value: 'tone', label: 'Tone' },
    { value: 'target_audience', label: 'Target audience' },
  ],
  chapter: [
    { value: 'title', label: 'Title' },
    { value: 'summary', label: 'Summary' },
  ],
  scene: [
    { value: 'summary', label: 'Summary' },
    { value: 'goal', label: 'Goal' },
    { value: 'setting', label: 'Setting' },
    { value: 'emotional_beat', label: 'Emotional beat' },
    { value: 'scene_type', label: 'Scene type' },
    { value: 'characters', label: 'Characters' },
  ],
}

const SPINE_TYPES = new Set(['concept', 'chapter', 'scene'])

export function focusLabel(f: { type: string, name: string } | null): string {
  if (!f) return 'Whole project'
  if (f.type === 'concept') return 'Concept'
  if (f.type === 'chapter') return `Chapter ${f.name}`
  if (f.type === 'scene') {
    const [c, s] = String(f.name).split('.')
    return `Scene ${s} of Ch. ${c}`
  }
  return f.name
}

// B45: ALL brainstorm logic, extracted from BrainstormDrawer so the workbench can dock it as
// a permanent pane. `variant` only changes the chrome (drawer = closable overlay column).
export default function BrainstormPanel({ projectName, variant, onClose, headerExtra }: {
  projectName: string, variant: 'drawer' | 'docked', onClose?: () => void, headerExtra?: React.ReactNode,
}) {
  const navigate = useNavigate()
  const { focus, setFocus, pendingFocus, pendingNonce, clearPending } = useBrainstormStore()
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [applyFor, setApplyFor] = useState<number | null>(null)
  const [useRefs, setUseRefs] = useState(true)
  const [verbosity, setVerbosity] = useState<'low' | 'medium' | 'high'>('medium')
  const [maxTokens, setMaxTokens] = useState<string>('')
  const [ents, setEnts] = useState<{ character: string[], location: string[], lore: string[], arc: string[] }>({ character: [], location: [], lore: [], arc: [] })
  const [sessions, setSessions] = useState<any[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [optionsOpen, setOptionsOpen] = useState(variant === 'drawer')
  // "Same object as a prior brainstorm" prompt: continue the old one or start fresh.
  const [focusPrompt, setFocusPrompt] = useState<{ focus: { type: string, name: string }, sessionId: string } | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const focusKey = focus ? `${focus.type}:${focus.name}` : ''

  // Defensive: a non-array response (proxy error page, mock gap) must degrade, not crash the app.
  const asList = (ss: any) => (Array.isArray(ss) ? ss : [])
  const refreshSessions = () => listSessions(projectName).then(ss => setSessions(asList(ss))).catch(() => {})

  // On mount: load entities + the session list, and pick an active session.
  useEffect(() => {
    if (!projectName) return
    Promise.all([
      listCharacters(projectName).catch(() => []),
      listLocations(projectName).catch(() => []),
      listLoreEntries(projectName).catch(() => []),
      listArcs(projectName).catch(() => []),
    ]).then(([c, l, lo, a]) => setEnts({
      character: (c || []).map((x: any) => x.name).filter(Boolean),
      location: (l || []).map((x: any) => x.name).filter(Boolean),
      lore: (lo || []).map((x: any) => x.name).filter(Boolean),
      arc: (a || []).map((x: any) => x.name).filter(Boolean),
    })).catch(() => {})
    listSessions(projectName).then((raw: any) => {
      const ss = asList(raw)
      setSessions(ss)
      // If opened targeting a specific object, the pending-focus resolver below selects the
      // session; don't pre-select the last active one (avoids a flash of the old chat).
      if (!pendingFocus) {
        setActiveId(prev => (prev && ss.some(s => s.id === prev)) ? prev : (ss[0]?.id || null))
      }
    }).catch(() => {})
  }, [projectName])  // eslint-disable-line react-hooks/exhaustive-deps

  // Resolve an explicitly-requested object ("Brainstorm this" button) to a per-object session.
  // Fires on every request (pendingNonce) even if the object equals the current focus.
  useEffect(() => {
    if (!projectName || !pendingFocus) return
    const pf = pendingFocus
    let cancelled = false
    ;(async () => {
      const ss: any[] = asList(await listSessions(projectName).catch(() => []))
      if (cancelled) return
      setSessions(ss)
      const sameFocus = (s: any) => s.focus && s.focus.type === pf.type && s.focus.name === pf.name
      const withHistory = (ss || []).filter(s => sameFocus(s) && (s.message_count || 0) > 0)
      withHistory.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')))
      if (withHistory.length > 0) {
        setFocusPrompt({ focus: pf, sessionId: withHistory[0].id })
      } else {
        const empty = (ss || []).find(s => sameFocus(s))
        if (empty) {
          setActiveId(empty.id)
        } else {
          const created = await createSession(projectName, { title: focusLabel(pf as any), focus: pf })
          if (cancelled) return
          await refreshSessions()
          setActiveId(created.id)
        }
      }
      clearPending()
    })()
    return () => { cancelled = true }
  }, [pendingNonce, projectName])  // eslint-disable-line react-hooks/exhaustive-deps

  // Load the active session's messages + persisted focus.
  useEffect(() => {
    if (!projectName || !activeId) { setMessages([]); return }
    getSession(projectName, activeId).then((s: any) => {
      setMessages(s.messages || [])
      if (s.focus || !useWorkbenchStore.getState().focusFollow || variant === 'drawer') {
        setFocus(s.focus || null)
      }
      setVerbosity((s.prefs?.verbosity as any) || 'medium')
      setMaxTokens(s.prefs?.max_tokens ? String(s.prefs.max_tokens) : '')
      setApplyFor(null)
    }).catch(() => {})
  }, [activeId, projectName])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setSending(true)
    setMessages(m => [...m, { role: 'user', content: text }, { role: 'assistant', content: '' }])
    try {
      await streamChat(projectName, text, tok => {
        setMessages(m => {
          const copy = m.slice()
          copy[copy.length - 1] = { role: 'assistant', content: copy[copy.length - 1].content + tok }
          return copy
        })
      }, focus, useRefs, activeId, { verbosity, max_tokens: maxTokens ? Number(maxTokens) : undefined })
    } catch (e: any) {
      setMessages(m => {
        const copy = m.slice()
        copy[copy.length - 1] = { role: 'assistant', content: (copy[copy.length - 1].content || '') + `\n[Error: ${e?.message || 'chat failed'}]` }
        return copy
      })
    } finally {
      setSending(false)
      refreshSessions()
    }
  }

  const changeVerbosity = (v: 'low' | 'medium' | 'high') => {
    setVerbosity(v)
    if (activeId) updateSession(projectName, activeId, { prefs: { verbosity: v } }).catch(() => {})
  }

  const commitMaxTokens = () => {
    const n = maxTokens.trim() ? Number(maxTokens) : null
    if (activeId) updateSession(projectName, activeId, { prefs: { max_tokens: n && n > 0 ? n : null } }).catch(() => {})
  }

  const clear = async () => {
    if (!activeId || !confirm("Clear this session's messages?")) return
    try { await clearSession(projectName, activeId) } catch {}
    setMessages([])
    refreshSessions()
  }

  // Same-object prompt actions.
  const continueFocused = () => {
    if (focusPrompt) setActiveId(focusPrompt.sessionId)
    setFocusPrompt(null)
  }
  const startNewFocused = async () => {
    if (!focusPrompt) return
    const pf = focusPrompt.focus
    setFocusPrompt(null)
    try {
      const created = await createSession(projectName, { title: focusLabel(pf as any), focus: pf })
      await refreshSessions()
      setActiveId(created.id)
      setMessages([])
    } catch {}
  }

  const newSession = async () => {
    const title = prompt('Name this session:', 'New chat')
    if (title === null) return
    try {
      const s = await createSession(projectName, { title: title || 'New chat' })
      await refreshSessions()
      setActiveId(s.id)
      setMessages([])
    } catch {}
  }

  const renameSession = async () => {
    if (!activeId) return
    const cur = sessions.find(s => s.id === activeId)
    const title = prompt('Rename session:', cur?.title || '')
    if (!title) return
    try { await updateSession(projectName, activeId, { title }); await refreshSessions() } catch {}
  }

  const removeSession = async () => {
    if (!activeId || !confirm('Delete this session and its messages?')) return
    try {
      await deleteSession(projectName, activeId)
      const ss = asList(await listSessions(projectName))
      setSessions(ss)
      setActiveId(ss[0]?.id || null)
    } catch {}
  }

  const doPreview = async () => {
    try {
      const r = await previewChat(projectName, { message: input, focus_type: focus?.type || null, focus_name: focus?.name || null, focus_aspect: focus?.aspect || null, use_references: useRefs })
      setPreview(r.system_prompt || '(empty)')
    } catch (e: any) {
      setPreview(`[Preview failed: ${e?.response?.data?.detail || e?.message || 'error'}]`)
    }
  }

  const changeFocus = (v: string) => {
    const nf = v ? { type: v.slice(0, v.indexOf(':')), name: v.slice(v.indexOf(':') + 1) } : null
    setFocus(nf)
    if (activeId) updateSession(projectName, activeId, { focus: nf }).catch(() => {})
  }

  const changeAspect = (v: string) => {
    if (!focus) return
    const nf = { ...focus, aspect: v || undefined }
    setFocus(nf)
    if (activeId) updateSession(projectName, activeId, { focus: nf }).catch(() => {})
  }

  // The current focus may be a spine item (set by focus-follow) that isn't a dropdown entity —
  // surface it as a dynamic option so the select never shows a lie.
  const spineOption = focus && SPINE_TYPES.has(focus.type) ? focusKey : null

  return (
    <div className={`relative flex flex-col h-full bg-gray-950 ${variant === 'drawer' ? 'border-l border-gray-800' : 'border border-gray-800 rounded-xl'}`}>
      {focusPrompt && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4" onClick={() => setFocusPrompt(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-sm p-5 space-y-4" onClick={e => e.stopPropagation()}>
            <div>
              <h2 className="text-base font-bold">Continue brainstorm for "{focusLabel(focusPrompt.focus as any)}"?</h2>
              <p className="text-sm text-gray-400 mt-1">You already have a brainstorm for this {focusPrompt.focus.type}. Pick up where you left off, or start a fresh one (the old one stays in your session list).</p>
            </div>
            <div className="flex flex-col gap-2">
              <button onClick={continueFocused} className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">Continue previous</button>
              <button onClick={startNewFocused} className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Start new</button>
              <button onClick={() => setFocusPrompt(null)} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles size={15} className="text-indigo-400 shrink-0" />
          <span className="text-sm font-medium">Brainstorm</span>
          {focus && <span className="text-xs text-indigo-300/90 truncate">· {focusLabel(focus)}</span>}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {headerExtra}
          <button onClick={clear} title="Clear conversation" className="text-gray-500 hover:text-red-400 p-1.5"><Trash2 size={14} /></button>
          {onClose && <button onClick={onClose} title="Close" className="text-gray-500 hover:text-gray-200 p-1.5 -mr-1"><X size={17} /></button>}
        </div>
      </div>

      <div className="px-3 py-2 border-b border-gray-800 flex items-center gap-1.5 shrink-0">
        <select value={activeId || ''} onChange={e => setActiveId(e.target.value)} title="Brainstorm session" className="flex-1 min-w-0 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
          {sessions.map(s => <option key={s.id} value={s.id}>{s.title}{s.message_count ? ` (${s.message_count})` : ''}</option>)}
        </select>
        <button onClick={newSession} title="New session" className="text-gray-400 hover:text-indigo-300 p-1.5"><Plus size={15} /></button>
        <button onClick={renameSession} title="Rename session" className="text-gray-400 hover:text-gray-200 p-1.5"><Pencil size={13} /></button>
        <button onClick={removeSession} title="Delete session" className="text-gray-500 hover:text-red-400 p-1.5"><Trash2 size={14} /></button>
      </div>

      <div className="border-b border-gray-800 shrink-0">
        <button onClick={() => setOptionsOpen(o => !o)}
          className="w-full px-3 py-1.5 text-left text-[11px] text-gray-500 hover:text-gray-300">
          {optionsOpen ? '▾' : '▸'} Focus &amp; options{!optionsOpen && focus ? ` — ${focusLabel(focus)}${focus.aspect ? ` · ${focus.aspect.replace(/_/g, ' ')}` : ''}` : ''}
        </button>
        {optionsOpen && (
          <div className="px-3 pb-2">
            <label className="text-xs text-gray-500 flex items-center gap-2">
              Focus
              <select value={focusKey} onChange={e => changeFocus(e.target.value)} className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
                <option value="">Whole project</option>
                <option value="concept:concept">📖 Concept (premise & hook)</option>
                <option value="world:World">🌍 World (setting & rules)</option>
                {spineOption && spineOption !== 'concept:concept' && <option value={spineOption}>▸ {focusLabel(focus)}</option>}
                {ents.character.length > 0 && <optgroup label="Characters">{ents.character.map(n => <option key={'character:' + n} value={'character:' + n}>{n}</option>)}</optgroup>}
                {ents.location.length > 0 && <optgroup label="Locations">{ents.location.map(n => <option key={'location:' + n} value={'location:' + n}>{n}</option>)}</optgroup>}
                {ents.lore.length > 0 && <optgroup label="Codex">{ents.lore.map(n => <option key={'lore:' + n} value={'lore:' + n}>{n}</option>)}</optgroup>}
                {ents.arc.length > 0 && <optgroup label="Arcs">{ents.arc.map(n => <option key={'arc:' + n} value={'arc:' + n}>{n}</option>)}</optgroup>}
              </select>
            </label>
            {focus && (
              <label className="text-xs text-gray-500 flex items-center gap-2 mt-2" title="Narrow the brainstorm (and Apply) to one property of this entity">
                Property
                <select value={focus.aspect || ''} onChange={e => changeAspect(e.target.value)} className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
                  <option value="">Any / All</option>
                  {(ASPECTS[focus.type] || []).map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                </select>
              </label>
            )}
            {focus && (
              <p className="text-[11px] text-indigo-400/80 mt-1">
                {focus.aspect
                  ? <>Developing only the <span className="font-medium">{(ASPECTS[focus.type] || []).find(a => a.value === focus.aspect)?.label || focus.aspect}</span> of {focusLabel(focus)}.</>
                  : <>Developing {focusLabel(focus)} — draws on the world, arcs &amp; connected lore as context, but only develops this.</>}
              </p>
            )}
            <label className="text-xs text-gray-500 flex items-center gap-2 mt-2" title="How long and detailed brainstorm responses are">
              Verbosity
              <select value={verbosity} onChange={e => changeVerbosity(e.target.value as any)} className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
                <option value="low">Low — succinct</option>
                <option value="medium">Medium — balanced</option>
                <option value="high">High — detailed</option>
              </select>
            </label>
            <label className="text-xs text-gray-500 flex items-center gap-2 mt-2" title="Max tokens per response. Overrides the verbosity cap when set — raise it if replies get cut off (local models: tokens are free).">
              Response length
              <input type="number" min="0" step="256" value={maxTokens} onChange={e => setMaxTokens(e.target.value)} onBlur={commitMaxTokens}
                placeholder="auto" className="w-24 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" />
              <span className="text-[10px] text-gray-600">tokens</span>
            </label>
            <div className="flex items-center justify-between mt-2">
              <label className="flex items-center gap-1.5 text-[11px] text-gray-400" title="Include imported reference material (References) as background source">
                <input type="checkbox" checked={useRefs} onChange={e => setUseRefs(e.target.checked)} />
                Use reference material
              </label>
              <button onClick={doPreview} title="See the exact prompt (lore + references) the AI will receive" className="flex items-center gap-1 text-[11px] text-gray-500 hover:text-indigo-300">
                <Eye size={12} /> Preview prompt
              </button>
            </div>
          </div>
        )}
      </div>

      {preview !== null && (
        <div className="absolute inset-0 z-10 bg-gray-950/95 flex flex-col p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-300">Assembled prompt (what the AI receives)</span>
            <button onClick={() => setPreview(null)} title="Close preview" className="text-gray-500 hover:text-gray-200 p-1.5 -m-1"><X size={16} /></button>
          </div>
          <pre className="flex-1 overflow-auto text-[11px] text-gray-300 whitespace-pre-wrap bg-gray-900 border border-gray-800 rounded p-2">{preview}</pre>
          <p className="text-[10px] text-gray-600 mt-2">This is the system prompt for the current Focus/message — no LLM call was made.</p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {messages.length === 0 && (
          <p className="text-xs text-gray-500 text-center py-8">
            Bounce ideas around — the AI sees this project's lore{focus ? <> and is focused on <b>{focusLabel(focus)}</b></> : ''}. Use <b>Apply</b> on a reply to save an idea.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            <div className={`inline-block max-w-[90%] text-left px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-indigo-900/50 border border-indigo-800' : 'bg-gray-800 border border-gray-700'}`}>
              {m.content || (sending && i === messages.length - 1 ? '…' : '')}
            </div>
            {m.role === 'assistant' && m.content && (
              <div className="mt-1 flex gap-3">
                {focus && SPINE_TYPES.has(focus.type) && (
                  <button onClick={() => setApplyFor(applyFor === i ? null : i)} className="text-xs text-green-400 hover:text-green-300">Apply to this item ▾</button>
                )}
                {(!focus || !SPINE_TYPES.has(focus.type)) && (
                  <button onClick={() => setApplyFor(applyFor === i ? null : i)} className="text-xs text-indigo-400 hover:text-indigo-300">Apply to lore ▾</button>
                )}
              </div>
            )}
            {m.role === 'assistant' && m.content && applyFor === i && (
              focus && SPINE_TYPES.has(focus.type)
                ? <ApplyToItem projectName={projectName} text={m.content} focus={focus} onDone={() => setApplyFor(null)} />
                : <ParseApply
                    projectName={projectName}
                    text={m.content}
                    focus={focus}
                    onDone={() => setApplyFor(null)}
                    onView={() => { onClose?.(); navigate(`/projects/${projectName}/lorebook`) }}
                  />
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="border-t border-gray-800 p-3 shrink-0">
        <div className="flex gap-2">
          <textarea
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm resize-none h-16"
            placeholder="Ask, plan, or brainstorm…  (Enter to send, Shift+Enter for newline)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          />
          <button onClick={send} disabled={sending || !input.trim()} className="px-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg disabled:opacity-50">
            {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  )
}

// B45: write a brainstorm reply into ONE field of the focused spine item (concept / chapter /
// scene). Nothing saves until the author reviews the (editable) text and clicks Save.
function ApplyToItem({ projectName, text, focus, onDone }: {
  projectName: string, text: string, focus: { type: string, name: string, aspect?: string }, onDone: () => void,
}) {
  const aspects = (ASPECTS[focus.type] || []).filter(a => !['scene_type', 'characters', 'title', 'tone'].includes(a.value) || focus.aspect === a.value)
  const [field, setField] = useState(focus.aspect && aspects.some(a => a.value === focus.aspect) ? focus.aspect : (aspects[0]?.value || 'summary'))
  const [value, setValue] = useState(text.trim())
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const bumpLore = useBrainstormStore(s => s.bumpLore)

  const save = async () => {
    setBusy(true); setErr('')
    try {
      if (focus.type === 'concept') {
        await updateProjectMeta(projectName, { [field]: value } as any)
      } else if (focus.type === 'chapter') {
        await updateChapterMeta(projectName, parseInt(focus.name), { [field]: value })
      } else {
        const [c, s] = String(focus.name).split('.').map(Number)
        const scenes = await listScenes(projectName, c)
        const scene = scenes.find((x: any) => x.scene_number === s)
        if (!scene) throw new Error(`Scene ${focus.name} not found`)
        await updateScene(projectName, c, s, { ...scene, [field]: value })
      }
      bumpTree(); bumpLore()
      onDone()
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || 'Save failed')
    } finally { setBusy(false) }
  }

  return (
    <div className="mt-2 p-2 bg-gray-900 border border-gray-700 rounded space-y-2 text-left">
      <label className="text-[11px] text-gray-500 flex items-center gap-2">
        Write into
        <select value={field} onChange={e => setField(e.target.value)} className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
          {aspects.map(a => <option key={a.value} value={a.value}>{focusLabel(focus)} — {a.label}</option>)}
        </select>
      </label>
      <textarea value={value} onChange={e => setValue(e.target.value)}
        className="w-full h-28 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs" />
      {err && <p className="text-[11px] text-red-400">{err}</p>}
      <div className="flex gap-2">
        <button onClick={save} disabled={busy} className="flex items-center gap-1 px-2.5 py-1 bg-green-700 hover:bg-green-600 rounded text-xs disabled:opacity-50">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} Save to {focus.type}
        </button>
        <button onClick={onDone} className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs">Cancel</button>
      </div>
    </div>
  )
}

// Parse a brainstorm reply into a multi-category proposal, then review & smart-merge it.
// When a lore Focus is active, the reply is decomposed straight into that entity's field set (B24).
export function ParseApply({ projectName, text, focus, onDone, onView }: { projectName: string, text: string, focus?: { type: string, name: string, aspect?: string } | null, onDone: () => void, onView: () => void }) {
  const [proposal, setProposal] = useState<Proposal | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [debug, setDebug] = useState<any>(null)
  const bumpLore = useBrainstormStore(s => s.bumpLore)

  const parse = async () => {
    setBusy(true); setError(''); setProposal(null); setDebug(null)
    try {
      const r = await parseChat(projectName, { text, focus_type: focus?.type || null, focus_name: focus?.name || null, focus_aspect: focus?.aspect || null })
      setProposal(r.proposal)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not parse this reply.')
    } finally {
      setBusy(false)
    }
  }

  const runDebug = async () => {
    setDebug({ loading: true })
    try {
      const r = await parseChatDebug(projectName, { text, focus_type: focus?.type || null, focus_name: focus?.name || null, focus_aspect: focus?.aspect || null })
      // eslint-disable-next-line no-console
      console.log('[brainstorm apply debug]', r)
      setDebug(r)
    } catch (e: any) {
      setDebug({ error: e?.response?.data?.detail || String(e) })
    }
  }

  useEffect(() => { parse() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mt-2 p-2 bg-gray-900 border border-gray-700 rounded text-left">
      {busy && <div className="flex items-center gap-2 text-xs text-gray-400 py-2"><Loader2 size={13} className="animate-spin" /> Parsing into lore…</div>}
      {error && (
        <div className="text-xs text-red-400 space-y-2">
          <p>{error}</p>
          <div className="flex gap-2">
            <button onClick={parse} className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">Retry</button>
            <button onClick={runDebug} className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-amber-300">Debug</button>
            <button onClick={onDone} className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">Cancel</button>
          </div>
          {debug && (
            <pre className="max-h-64 overflow-auto rounded bg-black/60 border border-gray-700 p-2 text-[10px] text-gray-300 whitespace-pre-wrap break-words">
              {debug.loading ? 'Running diagnostic…' : JSON.stringify(debug, null, 2)}
            </pre>
          )}
        </div>
      )}
      {proposal && (
        <LoreProposalReview projectName={projectName} proposal={proposal} onApplied={() => bumpLore()} onCancel={onDone} onView={onView} />
      )}
    </div>
  )
}
