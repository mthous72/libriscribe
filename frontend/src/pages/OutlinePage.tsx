import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getOutline, updateOutline, listScenes, updateScene, createScene, deleteScene, regenerateOutline } from '../api/client'
import { useUiStore } from '../store/uiSlice'
import { ArrowLeft, Save, Plus, Trash2, Lock, Unlock, RefreshCw } from 'lucide-react'

export default function OutlinePage() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const [outline, setOutline] = useState<any>(null)
  const [markdown, setMarkdown] = useState('')
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null)
  const [scenes, setScenes] = useState<any[]>([])
  const [editScene, setEditScene] = useState<any>(null)
  const [lockedChapters, setLockedChapters] = useState<Set<number>>(new Set())
  const [regenerating, setRegenerating] = useState(false)

  useEffect(() => {
    if (name) {
      getOutline(name).then(data => {
        setOutline(data)
        setMarkdown(data.outline_markdown || '')
      }).catch(() => {})
    }
  }, [name])

  useEffect(() => {
    if (name && selectedChapter) {
      listScenes(name, selectedChapter).then(setScenes).catch(() => setScenes([]))
    }
  }, [name, selectedChapter])

  const saveOutline = async () => {
    if (!name) return
    await updateOutline(name, { outline_markdown: markdown })
    useUiStore.getState().markClean()
    alert('Outline saved')
  }

  const saveScene = async () => {
    if (!name || !selectedChapter || !editScene) return
    await updateScene(name, selectedChapter, editScene.scene_number, editScene)
    useUiStore.getState().markClean()
    const updated = await listScenes(name, selectedChapter)
    setScenes(updated)
    setEditScene(null)
  }

  const addScene = async () => {
    if (!name || !selectedChapter) return
    const newNum = scenes.length + 1
    await createScene(name, selectedChapter, { scene_number: newNum, summary: 'New scene' })
    const updated = await listScenes(name, selectedChapter)
    setScenes(updated)
  }

  const removeScene = async (sceneNum: number) => {
    if (!name || !selectedChapter || !confirm('Delete this scene?')) return
    await deleteScene(name, selectedChapter, sceneNum)
    const updated = await listScenes(name, selectedChapter)
    setScenes(updated)
    setEditScene(null)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(`/projects/${name}`)} className="text-gray-400 hover:text-gray-200"><ArrowLeft size={20} /></button>
        <h1 className="text-2xl font-bold">Outline</h1>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Outline markdown editor */}
        <div className="col-span-2 space-y-2">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-medium text-gray-400">Outline Markdown</h2>
            <button onClick={saveOutline} className="flex items-center gap-1 px-3 py-1 bg-indigo-600 rounded text-xs"><Save size={12} /> Save</button>
          </div>
          <textarea
            value={markdown}
            onChange={e => { setMarkdown(e.target.value); useUiStore.getState().markDirty() }}
            className="w-full h-64 bg-gray-900 border border-gray-800 rounded-lg p-3 font-mono text-xs text-gray-300 resize-none"
          />

          {/* Scene editor */}
          {selectedChapter && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-sm font-medium">Chapter {selectedChapter} Scenes</h3>
                <button onClick={addScene} className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"><Plus size={12} /> Add Scene</button>
              </div>
              <div className="space-y-2">
                {scenes.map(s => (
                  <div key={s.scene_number} className="flex items-start gap-2 bg-gray-800 rounded p-2 text-xs">
                    <div className="flex-1 cursor-pointer" onClick={() => setEditScene({ ...s })}>
                      <span className="font-medium">Scene {s.scene_number}</span>
                      {s.scene_type && <span className="ml-2 px-1.5 py-0.5 bg-gray-700 rounded text-gray-300">{s.scene_type}</span>}
                      {s.target_word_count && <span className="ml-1 text-gray-500">~{s.target_word_count}w</span>}
                      <p className="text-gray-400 mt-0.5">{s.summary?.slice(0, 80)}</p>
                      <p className="text-gray-500 mt-0.5">Setting: {s.setting} | Characters: {s.characters?.join(', ')}</p>
                    </div>
                    <button onClick={() => removeScene(s.scene_number)} className="text-gray-600 hover:text-red-400"><Trash2 size={12} /></button>
                  </div>
                ))}
              </div>

              {editScene && (
                <div className="mt-4 space-y-2 border-t border-gray-700 pt-3">
                  <h4 className="text-xs font-medium text-gray-400">Edit Scene {editScene.scene_number}</h4>
                  <input className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" placeholder="Summary" value={editScene.summary} onChange={e => setEditScene({ ...editScene, summary: e.target.value })} />
                  <input className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" placeholder="Setting" value={editScene.setting} onChange={e => setEditScene({ ...editScene, setting: e.target.value })} />
                  <input className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" placeholder="Characters (comma-separated)" value={editScene.characters?.join(', ')} onChange={e => setEditScene({ ...editScene, characters: e.target.value.split(',').map((s: string) => s.trim()) })} />
                  <input className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" placeholder="Goal" value={editScene.goal} onChange={e => setEditScene({ ...editScene, goal: e.target.value })} />
                  <input className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" placeholder="Emotional Beat" value={editScene.emotional_beat} onChange={e => setEditScene({ ...editScene, emotional_beat: e.target.value })} />
                  <div className="flex gap-2">
                    <label className="flex-1">
                      <span className="text-xs text-gray-500">Scene Type</span>
                      <select className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" value={editScene.scene_type || ''} onChange={e => setEditScene({ ...editScene, scene_type: e.target.value })}>
                        <option value="">Auto</option>
                        <option value="action">Action</option>
                        <option value="dialogue">Dialogue</option>
                        <option value="introspective">Introspective</option>
                        <option value="exposition">Exposition</option>
                        <option value="transition">Transition</option>
                      </select>
                    </label>
                    <label className="w-32">
                      <span className="text-xs text-gray-500">Target Words</span>
                      <input type="number" className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs" placeholder="Optional" value={editScene.target_word_count || ''} onChange={e => setEditScene({ ...editScene, target_word_count: e.target.value ? parseInt(e.target.value) : null })} />
                    </label>
                  </div>
                  <button onClick={saveScene} className="px-3 py-1 bg-indigo-600 rounded text-xs">Save Scene</button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Chapter list */}
        <div className="col-span-1">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-sm font-medium text-gray-400">Chapters</h2>
            <button
              onClick={async () => {
                if (!name || regenerating) return
                const allChapters = outline?.chapters?.map((ch: any) => ch.chapter_number) || []
                const unlocked = allChapters.filter((n: number) => !lockedChapters.has(n))
                if (unlocked.length === 0) { alert('No unlocked chapters to regenerate'); return }
                if (!confirm(`Regenerate ${unlocked.length} unlocked chapter(s)?`)) return
                setRegenerating(true)
                try {
                  const result = await regenerateOutline(name, { locked_chapters: Array.from(lockedChapters), regenerate_chapters: unlocked })
                  setOutline({ ...outline, chapters: result.chapters })
                } catch { alert('Regeneration failed') }
                setRegenerating(false)
              }}
              disabled={regenerating}
              className="flex items-center gap-1 px-2 py-1 bg-amber-600 hover:bg-amber-500 rounded text-xs disabled:opacity-50"
            >
              <RefreshCw size={12} className={regenerating ? 'animate-spin' : ''} /> Regen Unlocked
            </button>
          </div>
          <div className="space-y-1">
            {outline?.chapters?.map((ch: any) => {
              const isLocked = lockedChapters.has(ch.chapter_number)
              return (
                <div
                  key={ch.chapter_number}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer ${selectedChapter === ch.chapter_number ? 'bg-indigo-900 border border-indigo-700' : 'bg-gray-800 hover:bg-gray-700'}`}
                >
                  <button
                    onClick={e => {
                      e.stopPropagation()
                      setLockedChapters(prev => {
                        const next = new Set(prev)
                        if (next.has(ch.chapter_number)) next.delete(ch.chapter_number)
                        else next.add(ch.chapter_number)
                        return next
                      })
                    }}
                    className={`shrink-0 ${isLocked ? 'text-amber-400' : 'text-gray-600 hover:text-gray-400'}`}
                    title={isLocked ? 'Locked (click to unlock)' : 'Unlocked (click to lock)'}
                  >
                    {isLocked ? <Lock size={14} /> : <Unlock size={14} />}
                  </button>
                  <div className="flex-1" onClick={() => setSelectedChapter(ch.chapter_number)}>
                    <span className="font-medium">Ch. {ch.chapter_number}</span>
                    <span className="text-gray-400 ml-2">{ch.title}</span>
                    <div className="text-xs text-gray-500 mt-0.5">{ch.scene_count} scenes</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
