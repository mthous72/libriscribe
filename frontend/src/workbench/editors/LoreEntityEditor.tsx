import { useEffect, useRef, useState } from 'react'
import { Sparkles, Trash2, Mic, Loader2 } from 'lucide-react'
import {
  listCharacters, updateCharacter, deleteCharacter,
  listLocations, updateLocation, deleteLocation,
  listLoreEntries, updateLoreEntry, deleteLoreEntry,
  listArcs, updateArc, deleteArc,
  listThreads, updateThread, deleteThread,
  getConnectionSuggestions, proposeVoiceProfile,
  type WorkbenchTree,
} from '../../api/client'
import {
  FieldEditor, VoiceProfileEditor,
  CHAR_FIELDS, LOC_FIELDS, LORE_FIELDS, ARC_FIELDS, THREAD_FIELDS,
} from '../../components/lore/fields'
import { useUiStore } from '../../store/uiSlice'
import ImpactHint from '../ImpactHint'
import { useBrainstormStore } from '../../store/brainstormSlice'
import { useWorkbenchStore } from '../../store/workbenchSlice'

type Kind = 'character' | 'location' | 'lore' | 'arc' | 'thread'

const CONFIG: Record<Kind, { fields: string[], list: (n: string) => Promise<any[]>, update: (n: string, e: string, b: any) => Promise<any>, remove: (n: string, e: string) => Promise<any> }> = {
  character: { fields: CHAR_FIELDS, list: listCharacters, update: updateCharacter, remove: deleteCharacter },
  location: { fields: LOC_FIELDS, list: listLocations, update: updateLocation, remove: deleteLocation },
  lore: { fields: LORE_FIELDS, list: listLoreEntries, update: updateLoreEntry, remove: deleteLoreEntry },
  arc: { fields: ARC_FIELDS, list: listArcs, update: updateArc, remove: deleteArc },
  thread: { fields: THREAD_FIELDS, list: listThreads, update: updateThread, remove: deleteThread },
}

// B45: one editor for every lore-record type — the same FieldEditor stack as the Lorebook
// page, addressed by tree selection instead of tabs.
export default function LoreEntityEditor({ projectName, kind, entityName, tree, numChapters }: {
  projectName: string, kind: Kind, entityName: string, tree: WorkbenchTree, numChapters: number,
}) {
  const [record, setRecord] = useState<any>(null)
  const [missing, setMissing] = useState(false)
  const [linkSuggestions, setLinkSuggestions] = useState<{ type: string, name: string }[]>([])
  const [voiceBusy, setVoiceBusy] = useState(false)
  const dirtyRef = useRef(false)
  const openBrainstorm = useBrainstormStore(s => s.openBrainstorm)
  const bumpLore = useBrainstormStore(s => s.bumpLore)
  const loreVersion = useBrainstormStore(s => s.loreVersion)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const setSelection = useWorkbenchStore(s => s.setSelection)

  useEffect(() => {
    let cancelled = false
    dirtyRef.current = false
    setMissing(false)
    CONFIG[kind].list(projectName).then(items => {
      if (cancelled) return
      const found = items.find((e: any) => e.name === entityName)
      if (found) setRecord({ ...found, _origName: found.name })
      else { setRecord(null); setMissing(true) }
    }).catch(() => { if (!cancelled) setMissing(true) })
    return () => { cancelled = true }
  }, [projectName, kind, entityName, loreVersion])

  useEffect(() => {
    let cancelled = false
    getConnectionSuggestions(projectName, kind, entityName)
      .then(r => { if (!cancelled) setLinkSuggestions(r.suggestions || []) })
      .catch(() => { if (!cancelled) setLinkSuggestions([]) })
    return () => { cancelled = true }
  }, [projectName, kind, entityName, loreVersion])

  const characterNames = tree.characters.map(c => c.name)
  const allEntityNames = [
    ...tree.characters, ...tree.locations, ...tree.lore, ...tree.arcs, ...tree.threads,
  ].map(e => e.name)

  if (missing) return <div className="text-sm text-gray-500">“{entityName}” no longer exists — it may have been renamed or deleted.</div>
  if (!record) return <div className="text-sm text-gray-500">Loading…</div>

  const save = async () => {
    try {
      await CONFIG[kind].update(projectName, record._origName || record.name, record)
      useUiStore.getState().markClean()
      dirtyRef.current = false
      bumpLore(); bumpTree()
      if (record.name !== record._origName) setSelection({ kind, name: record.name } as any)
    } catch { alert('Save failed') }
  }

  const remove = async () => {
    if (!confirm(`Delete "${entityName}"?`)) return
    try {
      await CONFIG[kind].remove(projectName, entityName)
      bumpLore(); bumpTree()
      setSelection(null)
    } catch (e: any) {
      alert(`Couldn't delete "${entityName}": ${e?.response?.data?.detail || e?.message || 'request failed'}`)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold capitalize">{kind === 'lore' ? 'Codex entry' : kind}: <span className="text-indigo-300">{entityName}</span></h2>
        <button onClick={remove} className="text-gray-600 hover:text-red-400 p-1.5" title="Delete"><Trash2 size={15} /></button>
      </div>
      <FieldEditor fields={CONFIG[kind].fields} data={record}
        onChange={(k, v) => { dirtyRef.current = true; setRecord({ ...record, [k]: v }) }}
        numChapters={numChapters} entityType={kind}
        characterNames={characterNames} allEntityNames={allEntityNames} suggestions={linkSuggestions} />
      {kind === 'character' && (
        <>
          <VoiceProfileEditor value={record.voice_profile}
            onChange={vp => { dirtyRef.current = true; useUiStore.getState().markDirty(); setRecord({ ...record, voice_profile: vp }) }} />
          <button onClick={async () => {
            if (record.voice_profile && Object.values(record.voice_profile).some((v: any) => v && String(v).length) &&
                !confirm(`Generate a new voice profile for ${entityName}? The current one is replaced in the editor (nothing saves until you click Save).`)) return
            setVoiceBusy(true)
            try {
              const r = await proposeVoiceProfile(projectName, entityName)
              dirtyRef.current = true
              useUiStore.getState().markDirty()
              setRecord((prev: any) => ({ ...prev, voice_profile: r.voice_profile }))
            } catch (e: any) { alert(e?.response?.data?.detail || 'Voice profile generation failed') }
            setVoiceBusy(false)
          }} disabled={voiceBusy}
            title="AI drafts speech patterns, tics, vocabulary and sample lines for this character — review, edit, then Save"
            className="mt-2 flex items-center gap-1 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs disabled:opacity-50">
            {voiceBusy ? <Loader2 size={12} className="animate-spin" /> : <Mic size={12} />} Generate voice profile (AI)
          </button>
        </>
      )}
      {kind === 'arc' && record.milestones?.length > 0 && (
        <div className="mt-4 border border-gray-700 rounded-lg p-3">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Milestones</h4>
          <div className="space-y-2">
            {record.milestones.map((m: any, i: number) => (
              <button key={i} onClick={() => setSelection({ kind: 'milestone', arc: entityName, index: i })}
                className="w-full text-left bg-gray-800 hover:bg-gray-700 rounded p-2 text-xs">
                <div className="flex justify-between">
                  <span className="font-medium">{m.name}</span>
                  <span className={`px-1.5 py-0.5 rounded ${m.status === 'completed' ? 'bg-green-900 text-green-300' : m.status === 'in_progress' ? 'bg-blue-900 text-blue-300' : 'bg-gray-700 text-gray-400'}`}>{m.status}</span>
                </div>
                <div className="text-gray-400 mt-1">{m.milestone_type} | Target: Ch.{m.target_chapter}{m.actual_chapter ? ` | Actual: Ch.${m.actual_chapter}` : ''}</div>
              </button>
            ))}
          </div>
        </div>
      )}
      <ImpactHint projectName={projectName} entityName={entityName} />
      <div className="mt-4 flex gap-2">
        <button onClick={save} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save</button>
        <button onClick={() => openBrainstorm({ type: kind, name: entityName })}
          title="Brainstorm this entry with the AI (uses surrounding lore as context)"
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1">
          <Sparkles size={14} /> Brainstorm this
        </button>
      </div>
    </div>
  )
}
