import { useEffect, useMemo, useState } from 'react'
import { applyParsed, extractFields, extractFieldsDebug, listCharacters, listLocations, listLoreEntries, listArcs } from '../api/client'
import { Loader2, Check, RefreshCw, Bug } from 'lucide-react'

// A reviewable lore proposal: records grouped by category, each with a new/update status
// and editable typed fields. Shared by the brainstorm Smart Apply and JSON import flows.
export interface ProposalRecord { name: string; status: 'new' | 'update'; fields: Record<string, string> }
export interface Proposal {
  characters?: ProposalRecord[]
  locations?: ProposalRecord[]
  lore?: ProposalRecord[]
  arcs?: ProposalRecord[]
  worldbuilding?: { status: 'new' | 'update'; fields: Record<string, string> }
}

interface RecState { _id: string; include: boolean; name: string; status: string; fields: Record<string, string>; reparsing?: boolean; note?: string }

const CATS: [keyof Proposal, string][] = [
  ['characters', 'Characters'],
  ['locations', 'Locations'],
  ['lore', 'Codex'],
  ['arcs', 'Arcs'],
]

function initState(p: Proposal) {
  const s: Record<string, RecState[]> & { worldbuilding?: RecState } = {} as any
  for (const [key] of CATS) {
    s[key as string] = ((p[key] as ProposalRecord[]) || []).map((r, i) => ({
      _id: `${key as string}-${i}`, include: true, name: r.name, status: r.status, fields: { ...r.fields },
    }))
  }
  if (p.worldbuilding) {
    s.worldbuilding = { _id: 'wb', include: true, name: 'Worldbuilding', status: p.worldbuilding.status, fields: { ...p.worldbuilding.fields } }
  }
  return s
}

const Badge = ({ status }: { status: string }) => (
  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide ${status === 'update' ? 'bg-amber-900/40 text-amber-300 border border-amber-800' : 'bg-green-900/40 text-green-300 border border-green-800'}`}>
    {status}
  </span>
)

export default function LoreProposalReview({
  projectName, proposal, onApplied, onCancel, onView,
}: {
  projectName: string
  proposal: Proposal
  onApplied?: (summary: any) => void
  onCancel: () => void
  onView?: () => void
}) {
  const [state, setState] = useState(() => initState(proposal))
  const [busy, setBusy] = useState(false)
  const [summary, setSummary] = useState<any | null>(null)
  const [error, setError] = useState('')
  // Names of existing records per category, so an imported entry can be pointed at an existing
  // entity (pulldown next to the name) to merge/update it instead of creating a new one.
  const [existing, setExisting] = useState<Record<string, string[]>>({ characters: [], locations: [], lore: [], arcs: [] })
  // Global lock: only one LLM re-parse runs at a time so we never fire concurrent LM Studio calls.
  const [reparsingActive, setReparsingActive] = useState(false)

  useEffect(() => {
    if (!projectName) return
    Promise.all([
      listCharacters(projectName).catch(() => []),
      listLocations(projectName).catch(() => []),
      listLoreEntries(projectName).catch(() => []),
      listArcs(projectName).catch(() => []),
    ]).then(([c, l, lo, a]) => setExisting({
      characters: (c || []).map((x: any) => x?.name).filter(Boolean),
      locations: (l || []).map((x: any) => x?.name).filter(Boolean),
      lore: (lo || []).map((x: any) => x?.name).filter(Boolean),
      arcs: (a || []).map((x: any) => x?.name).filter(Boolean),
    })).catch(() => {})
  }, [projectName])

  // An entry is an Update when its (trimmed, case-insensitive) name matches an existing record
  // of its current category — recomputed live as the name/type is edited or picked from the pulldown.
  const statusFor = (cat: string, name: string, fallback: string) => {
    const n = (name || '').trim().toLowerCase()
    if (!n) return fallback
    return (existing[cat] || []).some(e => e.toLowerCase() === n) ? 'update' : (fallback === 'update' ? 'new' : fallback)
  }

  const clone = (s: typeof state) => JSON.parse(JSON.stringify(s)) as typeof state

  const setRec = (cat: string, idx: number, patch: Partial<RecState>) => {
    setState(prev => { const c = clone(prev); Object.assign((c as any)[cat][idx], patch); return c })
  }
  const setField = (cat: string, idx: number, field: string, value: string) => {
    setState(prev => { const c = clone(prev); (c as any)[cat][idx].fields[field] = value; return c })
  }
  const setWb = (patch: Partial<RecState>) => setState(prev => { const c = clone(prev); Object.assign(c.worldbuilding!, patch); return c })
  const setWbField = (field: string, value: string) => setState(prev => { const c = clone(prev); c.worldbuilding!.fields[field] = value; return c })

  const findAndUpdate = (id: string, mut: (r: RecState) => void) => setState(prev => {
    const c = clone(prev)
    for (const [k] of CATS) {
      const arr = (c as any)[k] as RecState[] | undefined
      const i = (arr || []).findIndex(r => r._id === id)
      if (arr && i >= 0) { mut(arr[i]); break }
    }
    return c
  })

  // Re-parse an entry's raw content into a category's sub-fields via one LLM call. Serialized
  // behind `reparsingActive` so re-filing several entries never fires concurrent LM Studio calls,
  // and the outcome is surfaced (note) so a failed/empty parse isn't silently "all in background".
  const runExtract = async (id: string, name: string, content: string, category: string) => {
    if (reparsingActive) return
    setReparsingActive(true)
    findAndUpdate(id, r => { r.reparsing = true; r.note = '' })
    try {
      const res = await extractFields(projectName, { name, content, category })
      const fields = res?.fields || {}
      if (Object.keys(fields).length) findAndUpdate(id, r => { r.fields = fields; r.note = '' })
      else findAndUpdate(id, r => { r.note = 'empty' })  // model returned nothing usable
    } catch {
      findAndUpdate(id, r => { r.note = 'error' })        // no LLM configured / call failed
    } finally {
      findAndUpdate(id, r => { r.reparsing = false })
      setReparsingActive(false)
    }
  }

  const currentContent = (rec: RecState) => Object.values(rec.fields || {}).filter(Boolean).join('\n')

  // Reassign an entry's type (e.g. a World Info entry that's really a character), then re-parse
  // its content into that type's sub-fields. The move preserves content (description <-> background)
  // so it survives even if the re-parse is skipped or fails.
  const changeType = async (fromCat: string, idx: number, toCat: string) => {
    if (fromCat === toCat || reparsingActive) return
    const rec = (state as any)[fromCat]?.[idx] as RecState | undefined
    if (!rec) return
    const id = rec._id
    const content = currentContent(rec)

    setState(prev => {
      const c = clone(prev)
      const [moved] = (c as any)[fromCat].splice(idx, 1)
      if (moved) {
        const f = moved.fields || (moved.fields = {})
        if (toCat === 'characters' && f.description && !f.background) { f.background = f.description; delete f.description }
        else if (toCat !== 'characters' && f.background && !f.description) { f.description = f.background; delete f.background }
        ;(c as any)[toCat].push(moved)
      }
      return c
    })

    await runExtract(id, rec.name, content, toCat)
  }

  // Manually re-run the parse for an entry's current category (retry after a failed/empty parse,
  // or after editing the name/content).
  const reparseRecord = (cat: string, idx: number) => {
    const rec = (state as any)[cat]?.[idx] as RecState | undefined
    if (!rec || reparsingActive) return
    runExtract(rec._id, rec.name, currentContent(rec), cat)
  }

  // Diagnostic: fetch the full extraction round-trip (model, prompt, raw responses, parsed) for
  // one record and show it so we can see exactly where extraction breaks. Also logged to console.
  const [debug, setDebug] = useState<Record<string, any>>({})
  const runDebug = async (cat: string, idx: number) => {
    const rec = (state as any)[cat]?.[idx] as RecState | undefined
    if (!rec) return
    setDebug(d => ({ ...d, [rec._id]: { loading: true } }))
    try {
      const res = await extractFieldsDebug(projectName, { name: rec.name, content: currentContent(rec), category: cat })
      // eslint-disable-next-line no-console
      console.log('[lore extract debug]', res)
      setDebug(d => ({ ...d, [rec._id]: res }))
    } catch (e: any) {
      setDebug(d => ({ ...d, [rec._id]: { error: e?.response?.data?.detail || String(e) } }))
    }
  }

  const selectedCount = useMemo(() => {
    let n = 0
    for (const [key] of CATS) n += (state[key as string] || []).filter(r => r.include && r.name.trim()).length
    if (state.worldbuilding?.include) n += 1
    return n
  }, [state])

  const apply = async () => {
    const records: any = {}
    for (const [key] of CATS) {
      const recs = (state[key as string] || [])
        .filter(r => r.include && r.name.trim())
        .map(r => ({ name: r.name.trim(), fields: r.fields }))
      if (recs.length) records[key] = recs
    }
    if (state.worldbuilding?.include) records.worldbuilding = { fields: state.worldbuilding.fields }
    if (Object.keys(records).length === 0) { setError('Select at least one record to apply.'); return }
    setBusy(true); setError('')
    try {
      const s = await applyParsed(projectName, records)
      setSummary(s)
      onApplied?.(s)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to apply')
    } finally {
      setBusy(false)
    }
  }

  if (summary) {
    const parts = Object.entries(summary).filter(([, v]) => (v as number) > 0).map(([k, v]) => `${v} ${k}`)
    return (
      <div className="p-3 bg-green-900/20 border border-green-800 rounded text-sm text-green-200">
        <div className="flex items-center gap-2 font-medium"><Check size={15} /> Applied {parts.join(', ') || 'nothing'}.</div>
        <div className="mt-2 flex gap-3 text-xs">
          {onView && <button onClick={onView} className="underline hover:text-green-100">View in Lorebook</button>}
          <button onClick={onCancel} className="underline hover:text-green-100">Close</button>
        </div>
      </div>
    )
  }

  const hasAny = CATS.some(([k]) => (state[k as string] || []).length > 0) || !!state.worldbuilding

  return (
    <div className="flex flex-col gap-2 text-sm">
      <p className="text-xs text-gray-400">
        Review what will be saved. <b className="text-green-300">New</b> entries are created;{' '}
        <b className="text-amber-300">Update</b> entries fill empty fields and revise changed ones —
        anything not shown here is preserved. Use the type dropdown to re-file an entry
        (e.g. a World Info entry that's really a character), or the <i>match…</i> dropdown to point
        it at an existing record so it merges into that one. Re-parses run one at a time; edit or
        uncheck anything before applying.
      </p>

      {!hasAny && <p className="text-xs text-gray-500 italic">Nothing to review.</p>}

      <div className="max-h-[55vh] overflow-y-auto pr-1 space-y-3">
        {CATS.map(([key, label]) => {
          const recs = state[key as string] || []
          if (!recs.length) return null
          return (
            <div key={key as string}>
              <div className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">{label}</div>
              <div className="space-y-2">
                {recs.map((r, idx) => (
                  <div key={idx} className={`rounded border ${r.include ? 'border-gray-700 bg-gray-900' : 'border-gray-800 bg-gray-900/40 opacity-60'} p-2`}>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <input type="checkbox" checked={r.include} onChange={e => setRec(key as string, idx, { include: e.target.checked })} />
                      <input
                        value={r.name}
                        onChange={e => setRec(key as string, idx, { name: e.target.value })}
                        className="flex-1 min-w-[8rem] px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs font-medium"
                      />
                      {(existing[key as string] || []).length > 0 && (
                        <select
                          value=""
                          onChange={e => { if (e.target.value) setRec(key as string, idx, { name: e.target.value }) }}
                          title="Match an existing entry — its name is used so this merges into that record instead of creating a new one"
                          className="px-1 py-1 bg-gray-800 border border-gray-700 rounded text-[11px] text-gray-400 max-w-[7rem]"
                        >
                          <option value="">match…</option>
                          {(existing[key as string] || []).map(n => <option key={n} value={n}>{n}</option>)}
                        </select>
                      )}
                      <select
                        value={key as string}
                        onChange={e => changeType(key as string, idx, e.target.value)}
                        disabled={r.reparsing || reparsingActive}
                        title="Change this entry's type — its fields are re-parsed for the new type"
                        className="px-1.5 py-1 bg-gray-800 border border-gray-700 rounded text-[11px] text-gray-300 disabled:opacity-50"
                      >
                        {CATS.map(([k, lbl]) => <option key={k as string} value={k as string}>{lbl}</option>)}
                      </select>
                      <button
                        onClick={() => reparseRecord(key as string, idx)}
                        disabled={r.reparsing || reparsingActive}
                        title="Re-parse this entry's content into the fields for its current type"
                        className="p-1 text-gray-400 hover:text-indigo-300 disabled:opacity-40"
                      >
                        {r.reparsing ? <Loader2 size={12} className="animate-spin text-indigo-400" /> : <RefreshCw size={12} />}
                      </button>
                      <button
                        onClick={() => runDebug(key as string, idx)}
                        title="Diagnose: show the model, prompt, and raw LLM response for this entry"
                        className="p-1 text-gray-500 hover:text-amber-300"
                      >
                        <Bug size={12} />
                      </button>
                      <Badge status={statusFor(key as string, r.name, r.status)} />
                    </div>
                    {debug[r._id] && (
                      <pre className="mt-1 ml-6 max-h-64 overflow-auto rounded bg-black/60 border border-gray-700 p-2 text-[10px] text-gray-300 whitespace-pre-wrap break-words">
                        {debug[r._id].loading ? 'Running diagnostic…' : JSON.stringify(debug[r._id], null, 2)}
                      </pre>
                    )}
                    {r.note === 'empty' && (
                      <p className="mt-1 pl-6 text-[10px] text-amber-400/90">
                        Couldn't auto-parse into fields — content kept in {key === 'characters' ? 'Background' : 'Description'}. Edit below or re-parse.
                      </p>
                    )}
                    {r.note === 'error' && (
                      <p className="mt-1 pl-6 text-[10px] text-red-400/90">
                        Re-parse failed — check that a model is configured for this project, then retry.
                      </p>
                    )}
                    {r.include && Object.keys(r.fields).length > 0 && (
                      <div className="mt-2 space-y-1.5 pl-6">
                        {Object.entries(r.fields).map(([f, v]) => (
                          <div key={f}>
                            <label className="text-[10px] text-gray-500">{f.replace(/_/g, ' ')}</label>
                            <textarea
                              value={v}
                              onChange={e => setField(key as string, idx, f, e.target.value)}
                              rows={Math.min(4, Math.max(1, Math.ceil((v?.length || 0) / 48)))}
                              className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs resize-y"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}

        {state.worldbuilding && (
          <div>
            <div className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">Worldbuilding</div>
            <div className={`rounded border ${state.worldbuilding.include ? 'border-gray-700 bg-gray-900' : 'border-gray-800 bg-gray-900/40 opacity-60'} p-2`}>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={state.worldbuilding.include} onChange={e => setWb({ include: e.target.checked })} />
                <span className="flex-1 text-xs font-medium">Worldbuilding</span>
                <Badge status={state.worldbuilding.status} />
              </div>
              {state.worldbuilding.include && (
                <div className="mt-2 space-y-1.5 pl-6">
                  {Object.entries(state.worldbuilding.fields).map(([f, v]) => (
                    <div key={f}>
                      <label className="text-[10px] text-gray-500">{f.replace(/_/g, ' ')}</label>
                      <textarea
                        value={v}
                        onChange={e => setWbField(f, e.target.value)}
                        rows={Math.min(4, Math.max(1, Math.ceil((v?.length || 0) / 48)))}
                        className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs resize-y"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex items-center gap-2 pt-1">
        <button onClick={apply} disabled={busy || selectedCount === 0} className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded text-xs font-medium disabled:opacity-50 flex items-center gap-1">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Apply selected ({selectedCount})
        </button>
        <button onClick={onCancel} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs">Cancel</button>
      </div>
    </div>
  )
}
