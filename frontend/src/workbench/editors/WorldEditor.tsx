import { useEffect, useState } from 'react'
import { Sparkles, Wand2, Loader2 } from 'lucide-react'
import { getWorldbuilding, updateWorldbuilding, generateWorldField } from '../../api/client'
import { useUiStore } from '../../store/uiSlice'
import { useBrainstormStore } from '../../store/brainstormSlice'
import { useWorkbenchStore } from '../../store/workbenchSlice'

// B45: the world as a singleton lore node — per-field editing plus a per-field AI generate
// (one small grounded call per field; proposal fills the editor, nothing saves until Save).
export default function WorldEditor({ projectName }: { projectName: string }) {
  const [world, setWorld] = useState<any>(null)
  const [busyField, setBusyField] = useState('')
  const openBrainstorm = useBrainstormStore(s => s.openBrainstorm)
  const loreVersion = useBrainstormStore(s => s.loreVersion)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)

  useEffect(() => {
    getWorldbuilding(projectName).then(setWorld).catch(() => setWorld({}))
  }, [projectName, loreVersion])

  if (!world) return <div className="text-sm text-gray-500">Loading…</div>

  const fields = Object.keys(world).filter(k => typeof world[k] === 'string')
  const save = async () => {
    await updateWorldbuilding(projectName, world)
    useUiStore.getState().markClean()
    bumpTree()
  }

  const genField = async (f: string) => {
    if (world[f]?.trim() && !confirm(`Generate a proposal for "${f.replace(/_/g, ' ')}"? It replaces the text in the editor (nothing saves until you click Save Worldbuilding).`)) return
    setBusyField(f)
    try {
      const r = await generateWorldField(projectName, f)
      setWorld((prev: any) => ({ ...prev, [f]: r.proposed }))
      useUiStore.getState().markDirty()
    } catch (e: any) { alert(e?.response?.data?.detail || 'Generation failed') }
    setBusyField('')
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">World</h2>
      {fields.map(f => (
        <label key={f} className="block">
          <span className="text-xs text-gray-400 capitalize flex items-center justify-between">
            {f.replace(/_/g, ' ')}
            <button onClick={e => { e.preventDefault(); genField(f) }} disabled={!!busyField}
              title={`AI drafts this one field, grounded in your lore — review, edit, then Save`}
              className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] text-gray-500 hover:text-indigo-300 disabled:opacity-50 normal-case">
              {busyField === f ? <Loader2 size={10} className="animate-spin" /> : <Wand2 size={10} />} Generate
            </button>
          </span>
          <textarea
            className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-16"
            value={world[f] || ''}
            onChange={e => { setWorld({ ...world, [f]: e.target.value }); useUiStore.getState().markDirty() }}
          />
        </label>
      ))}
      <div className="flex gap-2">
        <button onClick={save} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Save Worldbuilding</button>
        <button onClick={() => openBrainstorm({ type: 'world', name: 'World' })}
          title="Brainstorm the world with the AI; Apply routes into these fields"
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-1">
          <Sparkles size={14} /> Brainstorm the world
        </button>
      </div>
    </div>
  )
}
