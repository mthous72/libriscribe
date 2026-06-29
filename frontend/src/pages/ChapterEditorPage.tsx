import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getChapter, saveChapter } from '../api/client'
import { useUiStore } from '../store/uiSlice'
import { ArrowLeft, Save } from 'lucide-react'

export default function ChapterEditorPage() {
  const { name, n } = useParams<{ name: string; n: string }>()
  const navigate = useNavigate()
  const [content, setContent] = useState('')
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (name && n) {
      getChapter(name, parseInt(n)).then(ch => {
        setContent(ch.content)
        setTitle(ch.title)
      }).catch(() => {})
    }
  }, [name, n])

  const handleSave = async () => {
    if (!name || !n) return
    setSaving(true)
    try {
      await saveChapter(name, parseInt(n), { chapter_number: parseInt(n), title, content, word_count: content.split(/\s+/).length })
      setDirty(false)
      useUiStore.getState().markClean()
    } catch (e) {
      alert('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(`/projects/${name}`)} className="text-gray-400 hover:text-gray-200">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold">Chapter {n}: {title}</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{content.split(/\s+/).length} words</span>
          {dirty && <span className="text-xs text-yellow-500">Unsaved</span>}
          <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm disabled:opacity-50">
            <Save size={14} /> {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
      <textarea
        value={content}
        onChange={e => { setContent(e.target.value); setDirty(true); useUiStore.getState().markDirty() }}
        className="w-full h-[calc(100vh-200px)] bg-gray-900 border border-gray-800 rounded-xl p-4 font-mono text-sm text-gray-200 resize-none focus:outline-none focus:border-indigo-600"
        spellCheck={false}
      />
    </div>
  )
}
