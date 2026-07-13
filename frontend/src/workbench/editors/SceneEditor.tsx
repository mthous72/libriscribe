import { useEffect, useRef, useState } from 'react'
import { Save, Trash2, Wand2, Loader2, Play } from 'lucide-react'
import { listScenes, updateScene, deleteScene, getSceneProse, writeScene, saveSceneProse, type WorkbenchTree } from '../../api/client'
import DiffView from '../../components/DiffView'
import { ListInput } from '../../components/lore/fields'
import { useUiStore } from '../../store/uiSlice'
import { useWorkbenchStore } from '../../store/workbenchSlice'
import { useGenerationStore } from '../../store/generationSlice'

// B45: a single scene as an item — outline fields, THIS scene's prose (editable), and the
// smallest AI bite: Write/Rewrite just this scene → diff → keep (spliced into the chapter).
export default function SceneEditor({ projectName, chapterNumber, sceneNumber, tree }: {
  projectName: string, chapterNumber: number, sceneNumber: number, tree: WorkbenchTree,
}) {
  const [scene, setScene] = useState<any>(null)
  const [missing, setMissing] = useState(false)
  const [prose, setProse] = useState<{ text: string, word_count: number } | null>(null)
  const [proseNote, setProseNote] = useState('')
  const [proseDirty, setProseDirty] = useState(false)
  const [unstructured, setUnstructured] = useState(false)
  const [guidance, setGuidance] = useState('')
  const [writing, setWriting] = useState(false)
  const [draft, setDraft] = useState<{ original: string, revised: string } | null>(null)
  const [writeErr, setWriteErr] = useState('')
  const setSelection = useWorkbenchStore(s => s.setSelection)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const treeVersion = useWorkbenchStore(s => s.treeVersion)
  const jobStatus = useGenerationStore(s => s.jobStatus)
  // Unsaved-edit guard for background refreshes (kept in a ref so the effect below sees the
  // live value, not a stale closure).
  const dirtyRef = useRef(false)
  const selKey = `${projectName}:${chapterNumber}.${sceneNumber}`
  const prevSelKey = useRef('')

  // Loads on selection change AND on treeVersion bumps (e.g. brainstorm "Apply to this item"
  // writing this scene's summary) — but a background bump never clobbers in-progress edits.
  useEffect(() => {
    const selectionChanged = prevSelKey.current !== selKey
    prevSelKey.current = selKey
    if (!selectionChanged && dirtyRef.current) return
    if (selectionChanged) {
      setScene(null); setProse(null); setDraft(null); setGuidance('')
      dirtyRef.current = false
      setProseDirty(false)
    }
    setMissing(false); setProseNote(''); setUnstructured(false); setWriteErr('')
    listScenes(projectName, chapterNumber).then(scenes => {
      const found = scenes.find((s: any) => s.scene_number === sceneNumber)
      if (found) setScene({ ...found })
      else { setScene(null); setMissing(true) }
    }).catch(() => setMissing(true))
    getSceneProse(projectName, chapterNumber, sceneNumber)
      .then(p => setProse({ text: p.text, word_count: p.word_count }))
      .catch((e: any) => {
        setProse(null)
        const status = e?.response?.status
        if (status === 409) {
          setUnstructured(true)
          setProseNote('This chapter’s prose has no scene markers — edit it at the chapter level.')
        } else setProseNote('')
      })
  }, [selKey, treeVersion])  // eslint-disable-line react-hooks/exhaustive-deps

  const runWrite = async () => {
    setWriting(true); setWriteErr(''); setDraft(null)
    try { setDraft(await writeScene(projectName, chapterNumber, sceneNumber, guidance)) }
    catch (e: any) { setWriteErr(e?.response?.data?.detail || 'Scene write failed') }
    finally { setWriting(false) }
  }

  const keepDraft = async () => {
    if (!draft) return
    try {
      await saveSceneProse(projectName, chapterNumber, sceneNumber, draft.revised)
      setProse({ text: draft.revised, word_count: draft.revised.split(/\s+/).filter(Boolean).length })
      setDraft(null)
      setProseDirty(false)
      dirtyRef.current = false
      bumpTree()
    } catch (e: any) { alert(e?.response?.data?.detail || 'Save failed') }
  }

  const saveEditedProse = async () => {
    if (!prose) return
    try {
      await saveSceneProse(projectName, chapterNumber, sceneNumber, prose.text)
      setProseDirty(false)
      dirtyRef.current = false
      useUiStore.getState().markClean()
      bumpTree()
    } catch (e: any) { alert(e?.response?.data?.detail || 'Save failed') }
  }

  if (missing) return <div className="text-sm text-gray-500">Scene {chapterNumber}.{sceneNumber} is not in the outline (it may have been deleted or renumbered).</div>
  if (!scene) return <div className="text-sm text-gray-500">Loading…</div>

  const set = (k: string, v: any) => { setScene({ ...scene, [k]: v }); dirtyRef.current = true; useUiStore.getState().markDirty() }
  const save = async () => {
    await updateScene(projectName, chapterNumber, sceneNumber, scene)
    useUiStore.getState().markClean()
    dirtyRef.current = proseDirty  // fields saved; prose edits (if any) still pending
    bumpTree()
  }
  const remove = async () => {
    if (!confirm(`Delete Scene ${sceneNumber} of Chapter ${chapterNumber}? Later scenes are renumbered.`)) return
    await deleteScene(projectName, chapterNumber, sceneNumber)
    bumpTree()
    setSelection({ kind: 'chapter', n: chapterNumber })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">
          <button onClick={() => setSelection({ kind: 'chapter', n: chapterNumber })} className="text-gray-500 hover:text-gray-300">Ch. {chapterNumber}</button>
          {' '}· Scene {sceneNumber}
        </h2>
        <button onClick={remove} className="text-gray-600 hover:text-red-400 p-1.5" title="Delete scene"><Trash2 size={15} /></button>
      </div>

      <div className="space-y-2 border border-gray-800 rounded-lg p-3">
        <label className="block">
          <span className="text-xs text-gray-400">Summary</span>
          <textarea className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-20"
            value={scene.summary || ''} onChange={e => set('summary', e.target.value)} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Setting</span>
          <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={scene.setting || ''} onChange={e => set('setting', e.target.value)} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Characters (comma-separated)</span>
          {/* ListInput commits on blur/Enter — parsing per keystroke ate the comma the
              user just typed (same fix as the lorebook list fields). */}
          <ListInput value={scene.characters || []} onCommit={v => set('characters', v)} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Goal</span>
          <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={scene.goal || ''} onChange={e => set('goal', e.target.value)} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Emotional beat</span>
          <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={scene.emotional_beat || ''} onChange={e => set('emotional_beat', e.target.value)} />
        </label>
        <div className="flex gap-2">
          <label className="flex-1">
            <span className="text-xs text-gray-500">Scene type</span>
            <select className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
              value={scene.scene_type || ''} onChange={e => set('scene_type', e.target.value)}>
              <option value="">Auto</option>
              <option value="action">Action</option>
              <option value="dialogue">Dialogue</option>
              <option value="introspective">Introspective</option>
              <option value="exposition">Exposition</option>
              <option value="transition">Transition</option>
            </select>
          </label>
          <label className="w-32">
            <span className="text-xs text-gray-500">Target words</span>
            <input type="number" className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
              placeholder="Optional" value={scene.target_word_count || ''}
              onChange={e => set('target_word_count', e.target.value ? parseInt(e.target.value) : null)} />
          </label>
        </div>
        <button onClick={save} className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs">
          <Save size={12} /> Save scene
        </button>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <h3 className="text-xs uppercase tracking-wide text-gray-500">
            Prose{prose ? ` · ${prose.word_count} words` : ''}
          </h3>
          {proseDirty && prose && (
            <button onClick={saveEditedProse} className="flex items-center gap-1 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-xs">
              <Save size={11} /> Save prose
            </button>
          )}
        </div>

        {!unstructured && (
          <div className="flex items-center gap-2">
            <input value={guidance} onChange={e => setGuidance(e.target.value)}
              placeholder='Optional direction — e.g. "slower burn", "end on the alarm going off"…'
              onKeyDown={e => { if (e.key === 'Enter') runWrite() }}
              className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs" />
            <button onClick={runWrite} disabled={writing || jobStatus === 'running'}
              title={prose ? 'Rewrite JUST this scene (full context: canon, recap, continuity) — you review a diff before anything saves' : 'Write JUST this scene — you review before anything saves'}
              className="flex items-center gap-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs disabled:opacity-50 shrink-0">
              {writing ? <Loader2 size={13} className="animate-spin" /> : (prose ? <Wand2 size={13} /> : <Play size={13} />)}
              {writing ? 'Writing…' : (prose ? 'Rewrite scene (AI)' : 'Write scene (AI)')}
            </button>
          </div>
        )}
        {writeErr && <div className="text-xs text-red-400">{writeErr}</div>}
        {draft && (
          <div className="space-y-2">
            <p className="text-[11px] text-gray-500">Review — <span className="text-green-400">green added</span>, <span className="text-red-400 line-through">red removed</span>. Only this scene's block changes in the chapter file.</p>
            <DiffView oldText={draft.original} newText={draft.revised} />
            <div className="flex gap-2">
              <button onClick={keepDraft} className="px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded-lg text-xs">Keep scene</button>
              <button onClick={() => setDraft(null)} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs">Discard</button>
            </div>
          </div>
        )}

        {prose ? (
          <textarea
            value={prose.text}
            onChange={e => { setProse({ ...prose, text: e.target.value }); setProseDirty(true); dirtyRef.current = true; useUiStore.getState().markDirty() }}
            className="w-full h-[38vh] bg-gray-900 border border-gray-800 rounded-lg p-3 font-mono text-sm text-gray-200 resize-none focus:outline-none focus:border-indigo-600"
            spellCheck={false} />
        ) : (
          <p className="text-xs text-gray-600">{proseNote || 'No prose for this scene yet — Write scene (AI) drafts it with full story context, or type it yourself after writing the chapter.'}</p>
        )}
      </div>
    </div>
  )
}
