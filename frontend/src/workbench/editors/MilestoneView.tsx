import { useState } from 'react'
import { Check, X, Save, Trash2 } from 'lucide-react'
import type { WorkbenchTree } from '../../api/client'
import { updateMilestone, deleteMilestone, actOnMilestoneProposal } from '../../api/client'
import { useWorkbenchStore } from '../../store/workbenchSlice'

const STATUSES = ['pending', 'in_progress', 'completed'] as const
const TYPES = ['inciting_incident', 'rising_action', 'escalation', 'climax', 'falling_action', 'resolution']

// B45 Slice 4: the full milestone editor — every field editable, status flips freely
// (typical of all flags), and AI verification proposals reviewed with evidence.
export default function MilestoneView({ projectName, arcName, index, tree }: {
  projectName: string, arcName: string, index: number, tree: WorkbenchTree,
}) {
  const setSelection = useWorkbenchStore(s => s.setSelection)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const arc = tree.arcs.find(a => a.name === arcName)
  const source = arc?.milestones?.[index]
  const [edit, setEdit] = useState<any>(source ? { ...source } : null)
  const [busy, setBusy] = useState(false)

  if (!source || !edit) return <div className="text-sm text-gray-500">Milestone not found — the arc may have changed.</div>

  const set = (k: string, v: any) => setEdit({ ...edit, [k]: v })
  const save = async () => {
    setBusy(true)
    try {
      await updateMilestone(projectName, arcName, index, {
        name: edit.name, milestone_type: edit.milestone_type,
        target_chapter: edit.target_chapter, actual_chapter: edit.actual_chapter,
        description: edit.description, status: edit.status,
      })
      bumpTree()
    } catch (e: any) { alert(e?.response?.data?.detail || 'Save failed') }
    setBusy(false)
  }

  const flip = async (status: string) => {
    setBusy(true)
    try {
      await updateMilestone(projectName, arcName, index, {
        status, ...(status !== 'completed' ? { actual_chapter: null } : {}),
      })
      setEdit({ ...edit, status, ...(status !== 'completed' ? { actual_chapter: null } : {}) })
      bumpTree()
    } catch (e: any) { alert(e?.response?.data?.detail || 'Flip failed') }
    setBusy(false)
  }

  const proposal = source.proposal
  const act = async (action: 'accept' | 'reject') => {
    setBusy(true)
    try {
      const r = await actOnMilestoneProposal(projectName, arcName, index, action)
      setEdit({ ...r.milestone })
      bumpTree()
    } catch (e: any) { alert(e?.response?.data?.detail || 'Action failed') }
    setBusy(false)
  }

  const remove = async () => {
    if (!confirm(`Delete milestone "${source.name}" from "${arcName}"?`)) return
    await deleteMilestone(projectName, arcName, index)
    bumpTree()
    setSelection({ kind: 'arc', name: arcName })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">
          <button onClick={() => setSelection({ kind: 'arc', name: arcName })} className="text-gray-500 hover:text-gray-300">{arcName}</button>
          {' '}· {source.name}
        </h2>
        <button onClick={remove} className="text-gray-600 hover:text-red-400 p-1.5" title="Delete milestone"><Trash2 size={15} /></button>
      </div>

      {proposal && (
        <div className={`border rounded-lg p-3 space-y-2 ${proposal.proposed_status === 'completed' ? 'border-green-800 bg-green-900/20' : proposal.proposed_status === 'not_completed' ? 'border-red-900 bg-red-900/10' : 'border-amber-800 bg-amber-900/20'}`}>
          <p className="text-xs font-medium text-amber-300">
            AI verification (Chapter {proposal.chapter}): {
              proposal.proposed_status === 'completed' ? 'this beat WAS delivered'
                : proposal.proposed_status === 'not_completed' ? 'this beat was NOT delivered'
                : 'uncertain'}
          </p>
          {proposal.evidence && (
            <blockquote className="text-xs text-gray-300 border-l-2 border-gray-600 pl-2 italic">“{proposal.evidence}”</blockquote>
          )}
          {proposal.reasoning && <p className="text-[11px] text-gray-400">{proposal.reasoning}</p>}
          <div className="flex gap-2">
            <button onClick={() => act('accept')} disabled={busy}
              title={proposal.proposed_status === 'completed' ? 'Mark completed with this chapter as actual' : proposal.proposed_status === 'not_completed' ? 'Re-open this milestone (clears any faked completion)' : 'Clear the proposal'}
              className="flex items-center gap-1 px-2.5 py-1 bg-green-700 hover:bg-green-600 rounded text-xs disabled:opacity-50">
              <Check size={12} /> Accept verdict
            </button>
            <button onClick={() => act('reject')} disabled={busy}
              className="flex items-center gap-1 px-2.5 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs disabled:opacity-50">
              <X size={12} /> Dismiss
            </button>
          </div>
          <p className="text-[10px] text-gray-600">The AI only proposes — you own the flag, and can flip it again anytime below.</p>
        </div>
      )}

      <div className="border border-gray-800 rounded-lg p-3 space-y-2">
        <label className="block">
          <span className="text-xs text-gray-400">Name</span>
          <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={edit.name || ''} onChange={e => set('name', e.target.value)} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Description (the planned beat)</span>
          <textarea className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-16"
            value={edit.description || ''} onChange={e => set('description', e.target.value)} />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="text-xs text-gray-400">Type</span>
            <select className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
              value={edit.milestone_type || 'rising_action'} onChange={e => set('milestone_type', e.target.value)}>
              {TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Target chapter</span>
            <select className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
              value={edit.target_chapter ?? ''} onChange={e => set('target_chapter', e.target.value ? Number(e.target.value) : null)}>
              <option value="">— unset —</option>
              {Array.from({ length: tree.num_chapters || tree.chapters.length }, (_, i) => i + 1).map(n => <option key={n} value={n}>Chapter {n}</option>)}
            </select>
          </label>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Status:</span>
          {STATUSES.map(s => (
            <button key={s} onClick={() => flip(s)} disabled={busy}
              className={`px-2 py-1 rounded text-xs capitalize ${edit.status === s
                ? (s === 'completed' ? 'bg-green-800 text-green-200' : s === 'in_progress' ? 'bg-blue-800 text-blue-200' : 'bg-gray-700 text-gray-200')
                : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
              {s.replace('_', ' ')}
            </button>
          ))}
          {edit.actual_chapter && <span className="text-[11px] text-gray-500 ml-auto">Actual: Ch.{edit.actual_chapter}</span>}
        </div>
        <button onClick={save} disabled={busy}
          className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs disabled:opacity-50">
          <Save size={12} /> Save milestone
        </button>
      </div>
    </div>
  )
}
