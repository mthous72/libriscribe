import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getChat, clearChat, applyChat, streamChat, listCharacters, listLocations, listLoreEntries, listArcs } from '../api/client'
import { MessageSquarePlus, X, Send, Trash2, Loader2, Sparkles } from 'lucide-react'

interface Msg { role: string; content: string }

const TARGETS = [
  { value: 'character', label: 'Character' },
  { value: 'location', label: 'Location' },
  { value: 'lore', label: 'Lore' },
  { value: 'arc', label: 'Arc' },
]

export default function BrainstormDrawer({ projectName }: { projectName: string }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [applyFor, setApplyFor] = useState<number | null>(null)
  const [ents, setEnts] = useState<{ character: string[], location: string[], lore: string[], arc: string[] }>({ character: [], location: [], lore: [], arc: [] })
  const [focusKey, setFocusKey] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  const focus = focusKey ? { type: focusKey.slice(0, focusKey.indexOf(':')), name: focusKey.slice(focusKey.indexOf(':') + 1) } : null

  useEffect(() => {
    if (!open || !projectName) return
    getChat(projectName).then(h => setMessages(h || [])).catch(() => {})
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
  }, [open, projectName])

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
      }, focus)
    } catch (e: any) {
      setMessages(m => {
        const copy = m.slice()
        copy[copy.length - 1] = { role: 'assistant', content: (copy[copy.length - 1].content || '') + `\n[Error: ${e?.message || 'chat failed'}]` }
        return copy
      })
    } finally {
      setSending(false)
    }
  }

  const clear = async () => {
    if (!confirm('Clear this brainstorm conversation?')) return
    try { await clearChat(projectName) } catch {}
    setMessages([])
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          title="Brainstorm with the AI (lore-aware)"
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-full shadow-lg text-sm font-medium"
        >
          <MessageSquarePlus size={16} /> Brainstorm
        </button>
      )}
      {open && (
        <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] bg-gray-950 border-l border-gray-800 flex flex-col shadow-2xl">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-400" />
              <span className="text-sm font-medium">Brainstorm</span>
              <span className="text-xs text-gray-500 truncate max-w-[120px]">{projectName}</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={clear} title="Clear conversation" className="text-gray-500 hover:text-red-400"><Trash2 size={15} /></button>
              <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-200"><X size={18} /></button>
            </div>
          </div>

          <div className="px-3 py-2 border-b border-gray-800">
            <label className="text-xs text-gray-500 flex items-center gap-2">
              Focus
              <select value={focusKey} onChange={e => setFocusKey(e.target.value)} className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
                <option value="">Whole project</option>
                {ents.character.length > 0 && <optgroup label="Characters">{ents.character.map(n => <option key={'character:' + n} value={'character:' + n}>{n}</option>)}</optgroup>}
                {ents.location.length > 0 && <optgroup label="Locations">{ents.location.map(n => <option key={'location:' + n} value={'location:' + n}>{n}</option>)}</optgroup>}
                {ents.lore.length > 0 && <optgroup label="Lore">{ents.lore.map(n => <option key={'lore:' + n} value={'lore:' + n}>{n}</option>)}</optgroup>}
                {ents.arc.length > 0 && <optgroup label="Arcs">{ents.arc.map(n => <option key={'arc:' + n} value={'arc:' + n}>{n}</option>)}</optgroup>}
              </select>
            </label>
            {focus && <p className="text-[11px] text-indigo-400/80 mt-1">Developing {focus.type} "{focus.name}" — draws on the world, arcs &amp; connected lore as context, but only develops this.</p>}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.length === 0 && (
              <p className="text-xs text-gray-500 text-center py-8">
                Bounce ideas around — the AI sees this project's lore. Use <b>Apply</b> on a reply
                to turn an idea into a character, location, lore entry, or arc.
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
                <div className={`inline-block max-w-[90%] text-left px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-indigo-900/50 border border-indigo-800' : 'bg-gray-800 border border-gray-700'}`}>
                  {m.content || (sending && i === messages.length - 1 ? '…' : '')}
                </div>
                {m.role === 'assistant' && m.content && (
                  <div className="mt-1">
                    <button onClick={() => setApplyFor(applyFor === i ? null : i)} className="text-xs text-indigo-400 hover:text-indigo-300">Apply to lore ▾</button>
                    {applyFor === i && (
                      <ApplyForm
                        projectName={projectName}
                        text={m.content}
                        onDone={() => setApplyFor(null)}
                        onView={() => { setOpen(false); navigate(`/projects/${projectName}/lorebook`) }}
                      />
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <div className="border-t border-gray-800 p-3">
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
      )}
    </>
  )
}

function ApplyForm({ projectName, text, onDone, onView }: { projectName: string, text: string, onDone: () => void, onView: () => void }) {
  const [targetType, setTargetType] = useState('character')
  const [entityName, setEntityName] = useState('')
  const [smart, setSmart] = useState(true)
  const [body, setBody] = useState(text)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  const apply = async () => {
    if (!entityName.trim()) { alert('Enter a name for the entry'); return }
    setBusy(true)
    try {
      await applyChat(projectName, { text: body, target_type: targetType, entity_name: entityName.trim(), smart })
      setDone(true)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to apply')
    } finally {
      setBusy(false)
    }
  }

  if (done) return (
    <div className="mt-2 p-2 bg-green-900/30 border border-green-800 rounded text-xs text-green-300">
      ✓ Created {targetType} "{entityName}". <button onClick={onView} className="underline">View in Lorebook</button> · <button onClick={onDone} className="underline">Close</button>
    </div>
  )

  return (
    <div className="mt-2 p-2 bg-gray-900 border border-gray-700 rounded space-y-2">
      <div className="flex gap-2">
        <select value={targetType} onChange={e => setTargetType(e.target.value)} className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs">
          {TARGETS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <input value={entityName} onChange={e => setEntityName(e.target.value)} placeholder="Name" className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" />
      </div>
      <textarea value={body} onChange={e => setBody(e.target.value)} className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs h-20 resize-none" />
      <label className="flex items-center gap-1 text-xs text-gray-400">
        <input type="checkbox" checked={smart} onChange={e => setSmart(e.target.checked)} /> Smart fill (extract fields with the LLM)
      </label>
      <div className="flex gap-2">
        <button onClick={apply} disabled={busy} className="px-2 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-xs disabled:opacity-50">{busy ? 'Applying…' : 'Apply'}</button>
        <button onClick={onDone} className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs">Cancel</button>
      </div>
    </div>
  )
}
