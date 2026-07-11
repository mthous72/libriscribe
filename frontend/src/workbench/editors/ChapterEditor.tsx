import { useEffect, useState } from 'react'
import { Save, Wand2, Loader2, Play, Eye, X, Flag } from 'lucide-react'
// (developScenes is imported lazily inside the action to keep the initial chunk lean)
import {
  getOutline, updateChapterMeta, getChapter, saveChapter, reviseChapter,
  previewContext, startGeneration, developScenes, verifyMilestones, type WorkbenchTree,
} from '../../api/client'
import DiffView from '../../components/DiffView'
import { useUiStore } from '../../store/uiSlice'
import { useWorkbenchStore } from '../../store/workbenchSlice'
import { useGenerationStore } from '../../store/generationSlice'

// B45: one chapter as an item — KB title/summary, its scene list (jump to scene nodes),
// and the prose with the existing Revise-with-AI diff loop. "Write chapter" hands off to the
// generation pipeline for exactly this chapter (progress shows in the strip below).
export default function ChapterEditor({ projectName, chapterNumber, tree }: {
  projectName: string, chapterNumber: number, tree: WorkbenchTree,
}) {
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [content, setContent] = useState<string | null>(null)
  const [metaDirty, setMetaDirty] = useState(false)
  const [proseDirty, setProseDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [ctx, setCtx] = useState<any | null>(null)
  const [guidance, setGuidance] = useState('')
  const [revising, setRevising] = useState(false)
  const [revision, setRevision] = useState<{ original: string, revised: string } | null>(null)
  const [revErr, setRevErr] = useState('')
  const [developing, setDeveloping] = useState(false)
  const [checking, setChecking] = useState(false)
  const [checkResults, setCheckResults] = useState<any[] | null>(null)
  const setSelection = useWorkbenchStore(s => s.setSelection)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const jobStatus = useGenerationStore(s => s.jobStatus)

  const treeCh = tree.chapters.find(c => c.chapter_number === chapterNumber)

  useEffect(() => {
    setMetaDirty(false); setProseDirty(false); setRevision(null); setRevErr(''); setGuidance('')
    getOutline(projectName).then(data => {
      const ch = (data.chapters || []).find((c: any) => c.chapter_number === chapterNumber)
      setTitle(ch?.title || '')
      setSummary(ch?.summary || '')
    }).catch(() => {})
    getChapter(projectName, chapterNumber)
      .then(ch => setContent(ch.content))
      .catch(() => setContent(null))
  }, [projectName, chapterNumber])

  const saveMeta = async () => {
    setSaving(true)
    try {
      await updateChapterMeta(projectName, chapterNumber, { title, summary })
      setMetaDirty(false)
      useUiStore.getState().markClean()
      bumpTree()
    } catch { alert('Save failed') }
    setSaving(false)
  }

  const saveProse = async (text: string) => {
    await saveChapter(projectName, chapterNumber, {
      chapter_number: chapterNumber, title, content: text, word_count: text.split(/\s+/).length,
    })
    setContent(text)
    setProseDirty(false)
    useUiStore.getState().markClean()
    bumpTree()
  }

  const runRevision = async () => {
    setRevising(true); setRevErr(''); setRevision(null)
    try { setRevision(await reviseChapter(projectName, chapterNumber, guidance)) }
    catch (e: any) { setRevErr(e?.response?.data?.detail || 'Revision failed') }
    finally { setRevising(false) }
  }

  const writeChapter = async () => {
    const verb = content ? 'REWRITE' : 'write'
    if (!confirm(`Use the AI to ${verb} Chapter ${chapterNumber}${content ? ' (replaces the current prose — a version snapshot is kept)' : ''}?`)) return
    try { await startGeneration(projectName, { chapter: chapterNumber }) }
    catch (e: any) { alert(e?.response?.data?.detail || 'Could not start') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-lg font-semibold">Chapter {chapterNumber}</h2>
        <div className="flex gap-2 items-center">
          <button onClick={async () => {
            try { setCtx(await previewContext(projectName, chapterNumber)) }
            catch (e: any) { setCtx({ context: `[Preview failed: ${e?.response?.data?.detail || 'error'}]`, token_estimate: 0 }) }
          }} title="See the lore/context the AI would receive for this chapter (no LLM call)"
            className="flex items-center gap-1 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs">
            <Eye size={13} /> AI context
          </button>
          {tree.arcs.some(a => a.milestones?.some((m: any) => m.target_chapter === chapterNumber)) && content !== null && (
            <button onClick={async () => {
              setChecking(true); setCheckResults(null)
              try {
                const r = await verifyMilestones(projectName, chapterNumber)
                setCheckResults(r.results)
                bumpTree()
              } catch (e: any) { alert(e?.response?.data?.detail || 'Milestone check failed') }
              setChecking(false)
            }} disabled={checking || jobStatus === 'running'}
              title="AI checks whether this chapter's prose actually delivered its planned milestones — you approve each flag"
              className="flex items-center gap-1 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs disabled:opacity-50">
              {checking ? <Loader2 size={13} className="animate-spin" /> : <Flag size={13} />} Check milestones (AI)
            </button>
          )}
          <button onClick={writeChapter} disabled={jobStatus === 'running'}
            title={content ? 'Regenerate this chapter with the AI' : 'Write this chapter with the AI'}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs disabled:opacity-50">
            <Play size={13} /> {content ? 'Rewrite chapter (AI)' : 'Write chapter (AI)'}
          </button>
        </div>
      </div>

      {ctx !== null && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center overflow-y-auto p-4" onClick={() => setCtx(null)}>
          <div className="bg-gray-950 border border-gray-800 rounded-lg shadow-2xl w-full max-w-2xl max-h-[calc(100vh-2rem)] flex flex-col p-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2 shrink-0">
              <div>
                <h2 className="text-sm font-semibold">AI context for Chapter {chapterNumber}</h2>
                <p className="text-[11px] text-gray-500">~{ctx.token_estimate} tokens · no LLM call</p>
              </div>
              <button onClick={() => setCtx(null)} className="text-gray-500 hover:text-gray-200 p-1.5 -m-1" title="Close"><X size={18} /></button>
            </div>
            <pre className="flex-1 min-h-0 overflow-auto text-[11px] text-gray-300 whitespace-pre-wrap bg-gray-900 border border-gray-800 rounded p-2">{ctx.context || '(no context assembled)'}</pre>
          </div>
        </div>
      )}

      {checkResults && (
        <div className="border border-amber-800 bg-amber-900/20 rounded-lg p-3 space-y-2">
          <p className="text-xs font-medium text-amber-300">Milestone check — verdicts are proposals; open each milestone to accept or dismiss:</p>
          {checkResults.map((r, i) => (
            <button key={i} onClick={() => setSelection({ kind: 'milestone', arc: r.arc, index: r.index })}
              className="w-full text-left text-xs bg-gray-900/60 hover:bg-gray-800 rounded p-2">
              <span className={`font-medium ${r.proposed_status === 'completed' ? 'text-green-400' : r.proposed_status === 'not_completed' ? 'text-red-400' : 'text-amber-400'}`}>
                {r.proposed_status === 'completed' ? '✓' : r.proposed_status === 'not_completed' ? '✗' : '?'} {r.name}
              </span>
              <span className="text-gray-500"> — {r.reasoning || r.proposed_status}</span>
            </button>
          ))}
        </div>
      )}

      {/* Outline data (KB) */}
      <div className="space-y-2 border border-gray-800 rounded-lg p-3">
        <label className="block">
          <span className="text-xs text-gray-400">Title</span>
          <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={title} onChange={e => { setTitle(e.target.value); setMetaDirty(true); useUiStore.getState().markDirty() }} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Summary</span>
          <textarea className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-24"
            value={summary} onChange={e => { setSummary(e.target.value); setMetaDirty(true); useUiStore.getState().markDirty() }} />
        </label>
        {metaDirty && (
          <button onClick={saveMeta} disabled={saving}
            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs disabled:opacity-50">
            <Save size={12} /> Save outline data
          </button>
        )}
      </div>

      {/* Scenes */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="text-xs uppercase tracking-wide text-gray-500">Scenes</h3>
          <button onClick={async () => {
            const has = (treeCh?.scenes?.length || 0) > 0
            if (!confirm(has
              ? `REGENERATE the scene outline for Chapter ${chapterNumber}? Its current ${treeCh!.scenes.length} scene brief(s) are replaced (prose files are untouched).`
              : `Generate the scene outline for Chapter ${chapterNumber} from its summary?`)) return
            setDeveloping(true)
            try { await developScenes(projectName, chapterNumber); bumpTree() }
            catch (e: any) { alert(e?.response?.data?.detail || 'Develop scenes failed') }
            setDeveloping(false)
          }} disabled={developing}
            title="Generate/regenerate this chapter's scene briefs from its summary (validate-and-retry)"
            className="flex items-center gap-1 px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded text-[11px] disabled:opacity-50">
            {developing ? <Loader2 size={11} className="animate-spin" /> : <Wand2 size={11} />} Develop scenes (AI)
          </button>
        </div>
        <div className="space-y-1">
          {(treeCh?.scenes || []).map(sc => (
            <button key={sc.scene_number}
              onClick={() => setSelection({ kind: 'scene', chapter: chapterNumber, scene: sc.scene_number })}
              className="w-full text-left px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full shrink-0 ${sc.has_prose ? 'bg-green-500' : sc.summary_set ? 'bg-blue-400' : 'bg-gray-600'}`} />
              Scene {sc.scene_number}
              {sc.word_count > 0 && <span className="ml-auto text-gray-500">{sc.word_count}w</span>}
            </button>
          ))}
          {(!treeCh || treeCh.scenes.length === 0) && (
            <p className="text-xs text-gray-600">No scenes outlined — use “Develop remaining” on the Outline node.</p>
          )}
        </div>
      </div>

      {/* Prose */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <h3 className="text-xs uppercase tracking-wide text-gray-500">Prose{content ? ` · ${content.split(/\s+/).length} words` : ''}</h3>
          {content !== null && (
            <div className="flex gap-2 items-center">
              {proseDirty && (
                <button onClick={() => saveProse(content)} className="flex items-center gap-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs">
                  <Save size={12} /> Save prose
                </button>
              )}
            </div>
          )}
        </div>
        {content === null ? (
          <p className="text-xs text-gray-600">Not written yet.</p>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <input value={guidance} onChange={e => setGuidance(e.target.value)}
                placeholder='Revision notes — e.g. "tighten the middle", "more tension"…'
                onKeyDown={e => { if (e.key === 'Enter') runRevision() }}
                className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs" />
              <button onClick={runRevision} disabled={revising}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs disabled:opacity-50">
                {revising ? <Loader2 size={13} className="animate-spin" /> : <Wand2 size={13} />} {revising ? 'Revising…' : 'Revise with AI'}
              </button>
            </div>
            {revErr && <div className="text-xs text-red-400">{revErr}</div>}
            {revision && (
              <div className="space-y-2">
                <p className="text-[11px] text-gray-500">Review — <span className="text-green-400">green added</span>, <span className="text-red-400 line-through">red removed</span>. Nothing saves until you keep it.</p>
                <DiffView oldText={revision.original} newText={revision.revised} />
                <div className="flex gap-2">
                  <button onClick={async () => { await saveProse(revision.revised); setRevision(null) }} className="px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded-lg text-xs">Keep revision</button>
                  <button onClick={() => setRevision(null)} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs">Discard</button>
                </div>
              </div>
            )}
            <textarea value={content}
              onChange={e => { setContent(e.target.value); setProseDirty(true); useUiStore.getState().markDirty() }}
              className="w-full h-[45vh] bg-gray-900 border border-gray-800 rounded-xl p-3 font-mono text-sm text-gray-200 resize-none focus:outline-none focus:border-indigo-600"
              spellCheck={false} />
          </>
        )}
      </div>
    </div>
  )
}
