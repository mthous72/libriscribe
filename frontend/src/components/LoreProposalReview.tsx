import { useMemo, useState } from 'react'
import { applyParsed } from '../api/client'
import { Loader2, Check } from 'lucide-react'

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

interface RecState { include: boolean; name: string; status: string; fields: Record<string, string> }

const CATS: [keyof Proposal, string][] = [
  ['characters', 'Characters'],
  ['locations', 'Locations'],
  ['lore', 'Codex'],
  ['arcs', 'Arcs'],
]

function initState(p: Proposal) {
  const s: Record<string, RecState[]> & { worldbuilding?: RecState } = {} as any
  for (const [key] of CATS) {
    s[key as string] = ((p[key] as ProposalRecord[]) || []).map(r => ({
      include: true, name: r.name, status: r.status, fields: { ...r.fields },
    }))
  }
  if (p.worldbuilding) {
    s.worldbuilding = { include: true, name: 'Worldbuilding', status: p.worldbuilding.status, fields: { ...p.worldbuilding.fields } }
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

  const clone = (s: typeof state) => JSON.parse(JSON.stringify(s)) as typeof state

  const setRec = (cat: string, idx: number, patch: Partial<RecState>) => {
    setState(prev => { const c = clone(prev); Object.assign((c as any)[cat][idx], patch); return c })
  }
  const setField = (cat: string, idx: number, field: string, value: string) => {
    setState(prev => { const c = clone(prev); (c as any)[cat][idx].fields[field] = value; return c })
  }
  const setWb = (patch: Partial<RecState>) => setState(prev => { const c = clone(prev); Object.assign(c.worldbuilding!, patch); return c })
  const setWbField = (field: string, value: string) => setState(prev => { const c = clone(prev); c.worldbuilding!.fields[field] = value; return c })

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
        anything not shown here is preserved. Uncheck or edit anything before applying.
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
                    <div className="flex items-center gap-2">
                      <input type="checkbox" checked={r.include} onChange={e => setRec(key as string, idx, { include: e.target.checked })} />
                      <input
                        value={r.name}
                        onChange={e => setRec(key as string, idx, { name: e.target.value })}
                        className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs font-medium"
                      />
                      <Badge status={r.status} />
                    </div>
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
