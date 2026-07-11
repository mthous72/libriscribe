import { useEffect, useState } from 'react'
import { Save, Sparkles, RefreshCw, Lock, Unlock } from 'lucide-react'
import { getOutline, updateOutline, developOutline, regenerateOutline } from '../../api/client'
import { useUiStore } from '../../store/uiSlice'
import { useWorkbenchStore } from '../../store/workbenchSlice'

// B45: the outline node — markdown, the additive "Develop remaining" (B44), and the
// destructive lock-protected "Rewrite unlocked…" absorbed from the old Outline page (Slice 6).
export default function OutlineEditor({ projectName }: { projectName: string }) {
  const [outline, setOutline] = useState<any>(null)
  const [markdown, setMarkdown] = useState('')
  const [developing, setDeveloping] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [lockedChapters, setLockedChapters] = useState<Set<number>>(new Set())
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const setSelection = useWorkbenchStore(s => s.setSelection)

  useEffect(() => {
    getOutline(projectName).then(data => {
      setOutline(data)
      setMarkdown(data.outline_markdown || '')
      // Safe by default: developed chapters start LOCKED (B44).
      setLockedChapters(new Set((data.chapters || [])
        .filter((ch: any) => (ch.scene_count || 0) > 0)
        .map((ch: any) => ch.chapter_number)))
    }).catch(() => {})
  }, [projectName])

  const save = async () => {
    await updateOutline(projectName, { outline_markdown: markdown })
    useUiStore.getState().markClean()
    bumpTree()
  }

  const develop = async () => {
    if (developing) return
    const chapters = outline?.chapters || []
    const remaining = chapters.filter((ch: any) => (ch.scene_count || 0) === 0).map((ch: any) => ch.chapter_number)
    if (remaining.length === 0) { alert('Every chapter already has scenes — nothing to develop.'); return }
    const done = chapters.filter((ch: any) => (ch.scene_count || 0) > 0).map((ch: any) => ch.chapter_number)
    if (!confirm(`Develop chapters ${remaining.join(', ')} (summaries where missing, then scenes).\n\nChapters ${done.join(', ') || '—'} stay exactly as they are.`)) return
    setDeveloping(true)
    try {
      const result = await developOutline(projectName)
      setOutline({ ...outline, chapters: result.chapters })
      bumpTree()
    } catch (err: any) { alert(err?.response?.data?.detail || 'Develop failed') }
    setDeveloping(false)
  }

  const rewriteUnlocked = async () => {
    if (regenerating) return
    const all = (outline?.chapters || []).map((ch: any) => ch.chapter_number)
    const unlocked = all.filter((n: number) => !lockedChapters.has(n))
    if (unlocked.length === 0) { alert('All chapters are locked — unlock the ones you want rewritten.'); return }
    if (!confirm(`This REWRITES chapters ${unlocked.join(', ')} from scratch (their current summaries and scenes are replaced).\n\nLocked chapters ${Array.from(lockedChapters).sort((a, b) => a - b).join(', ') || '—'} are untouched.`)) return
    setRegenerating(true)
    try {
      const result = await regenerateOutline(projectName, { locked_chapters: Array.from(lockedChapters), regenerate_chapters: unlocked })
      setOutline({ ...outline, chapters: result.chapters })
      bumpTree()
    } catch { alert('Regeneration failed') }
    setRegenerating(false)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-lg font-semibold">Outline</h2>
        <div className="flex gap-2 flex-wrap">
          <button onClick={develop} disabled={developing || regenerating}
            title="Continue the outline: fill in placeholder chapters and add scenes where missing. Never touches developed chapters."
            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs disabled:opacity-50">
            <Sparkles size={13} className={developing ? 'animate-pulse' : ''} /> Develop remaining
          </button>
          <button onClick={rewriteUnlocked} disabled={regenerating || developing}
            title="Rewrite the unlocked chapters from scratch. Lock anything you want to keep."
            className="flex items-center gap-1 px-3 py-1.5 bg-amber-700 hover:bg-amber-600 rounded-lg text-xs disabled:opacity-50">
            <RefreshCw size={13} className={regenerating ? 'animate-spin' : ''} /> Rewrite unlocked…
          </button>
          <button onClick={save} className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs">
            <Save size={13} /> Save
          </button>
        </div>
      </div>
      <textarea
        value={markdown}
        onChange={e => { setMarkdown(e.target.value); useUiStore.getState().markDirty() }}
        className="w-full h-72 bg-gray-900 border border-gray-800 rounded-lg p-3 font-mono text-xs text-gray-300 resize-none"
      />
      <div className="space-y-1">
        <h3 className="text-xs uppercase tracking-wide text-gray-500">Chapters <span className="normal-case text-gray-600">(lock = protected from “Rewrite unlocked”)</span></h3>
        {(outline?.chapters || []).map((ch: any) => {
          const isLocked = lockedChapters.has(ch.chapter_number)
          return (
            <div key={ch.chapter_number} className="flex items-center gap-1 px-2 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">
              <button
                onClick={() => setLockedChapters(prev => {
                  const next = new Set(prev)
                  next.has(ch.chapter_number) ? next.delete(ch.chapter_number) : next.add(ch.chapter_number)
                  return next
                })}
                className={`shrink-0 p-1.5 ${isLocked ? 'text-amber-400' : 'text-gray-600 hover:text-gray-400'}`}
                title={isLocked ? 'Locked (click to unlock)' : 'Unlocked (click to lock)'}>
                {isLocked ? <Lock size={13} /> : <Unlock size={13} />}
              </button>
              <button onClick={() => setSelection({ kind: 'chapter', n: ch.chapter_number })} className="flex-1 text-left min-w-0">
                <span className="font-medium">Ch. {ch.chapter_number}</span>
                <span className="text-gray-400 ml-2">{ch.title}</span>
                <span className="text-xs text-gray-500 ml-2">{ch.scene_count} scenes</span>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
