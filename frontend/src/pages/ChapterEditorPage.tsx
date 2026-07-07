import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getChapter, saveChapter, previewContext, reviseChapter } from '../api/client'
import { useUiStore } from '../store/uiSlice'
import { ArrowLeft, Save, Eye, X, Loader2, Wand2 } from 'lucide-react'
import DiffView from '../components/DiffView'

export default function ChapterEditorPage() {
  const { name, n } = useParams<{ name: string; n: string }>()
  const navigate = useNavigate()
  const [content, setContent] = useState('')
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [ctx, setCtx] = useState<any | null>(null)
  const [loadingCtx, setLoadingCtx] = useState(false)
  // B34/B35: guided revision with a keep/discard diff — never saves without your choice.
  const [showRevise, setShowRevise] = useState(false)
  const [guidance, setGuidance] = useState('')
  const [revising, setRevising] = useState(false)
  const [revision, setRevision] = useState<{ original: string, revised: string } | null>(null)
  const [revErr, setRevErr] = useState('')

  const runRevision = async () => {
    if (!name || !n) return
    setRevising(true); setRevErr(''); setRevision(null)
    try { setRevision(await reviseChapter(name, parseInt(n), guidance)) }
    catch (e: any) { setRevErr(e?.response?.data?.detail || 'Revision failed') }
    finally { setRevising(false) }
  }

  const keepRevision = async () => {
    if (!revision || !name || !n) return
    setContent(revision.revised)
    setDirty(false)
    try {
      await saveChapter(name, parseInt(n), { chapter_number: parseInt(n), title, content: revision.revised, word_count: revision.revised.split(/\s+/).length })
      useUiStore.getState().markClean()
    } catch { alert('Failed to save the revision') }
    setRevision(null); setShowRevise(false)
  }

  const previewCtx = async () => {
    if (!name || !n) return
    setLoadingCtx(true)
    try { setCtx(await previewContext(name, parseInt(n))) }
    catch (e: any) { setCtx({ context: `[Preview failed: ${e?.response?.data?.detail || 'error'}]`, token_estimate: 0 }) }
    finally { setLoadingCtx(false) }
  }

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => navigate(`/projects/${name}`)} className="text-gray-400 hover:text-gray-200 shrink-0 p-1.5 -m-1.5" title="Back to project">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold truncate">Chapter {n}: {title}</h1>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-gray-500">{content.split(/\s+/).length} words</span>
          {dirty && <span className="text-xs text-yellow-500">Unsaved</span>}
          <button onClick={previewCtx} disabled={loadingCtx} title="See the lore/context the AI would receive to write this chapter (no LLM call)" className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm disabled:opacity-50">
            {loadingCtx ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />} Preview AI context
          </button>
          <button onClick={() => setShowRevise(!showRevise)} title="Give revision notes; the AI rewrites the chapter and shows you a diff — you keep or discard" className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">
            <Wand2 size={14} /> Revise with AI
          </button>
          <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm disabled:opacity-50">
            <Save size={14} /> {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {ctx !== null && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center overflow-y-auto p-4" onClick={() => setCtx(null)}>
          <div className="bg-gray-950 border border-gray-800 rounded-lg shadow-2xl w-full max-w-2xl max-h-[calc(100vh-2rem)] flex flex-col p-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2 shrink-0">
              <div>
                <h2 className="text-sm font-semibold">AI context for Chapter {n}</h2>
                <p className="text-[11px] text-gray-500">The lore/context injected into the chapter-writing prompt · ~{ctx.token_estimate} tokens · no LLM call</p>
              </div>
              <button onClick={() => setCtx(null)} className="text-gray-500 hover:text-gray-200 p-1.5 -m-1 shrink-0" title="Close"><X size={18} /></button>
            </div>
            <pre className="flex-1 min-h-0 overflow-auto text-[11px] text-gray-300 whitespace-pre-wrap bg-gray-900 border border-gray-800 rounded p-2">{ctx.context || '(no context assembled — add lore, or write earlier chapters)'}</pre>
          </div>
        </div>
      )}

      {showRevise && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2">
            <input value={guidance} onChange={e => setGuidance(e.target.value)}
              placeholder='Revision notes — e.g. "tighten the middle", "more tension in the confrontation"…'
              onKeyDown={e => { if (e.key === 'Enter') runRevision() }}
              className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm" />
            <button onClick={runRevision} disabled={revising} className="flex items-center gap-1 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm disabled:opacity-50">
              {revising ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} {revising ? 'Revising…' : 'Revise'}
            </button>
          </div>
          {revErr && <div className="text-xs text-red-400">{revErr}</div>}
          {revision && (
            <>
              <p className="text-[11px] text-gray-500">Review the changes — <span className="text-green-400">green = added</span>, <span className="text-red-400 line-through">red = removed</span>. Nothing is saved until you keep it.</p>
              <DiffView oldText={revision.original} newText={revision.revised} />
              <div className="flex gap-2">
                <button onClick={keepRevision} className="px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded-lg text-sm">Keep revision</button>
                <button onClick={() => setRevision(null)} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Discard</button>
              </div>
            </>
          )}
        </div>
      )}

      <textarea
        value={content}
        onChange={e => { setContent(e.target.value); setDirty(true); useUiStore.getState().markDirty() }}
        className="w-full h-[65vh] sm:h-[calc(100vh-200px)] bg-gray-900 border border-gray-800 rounded-xl p-4 font-mono text-sm text-gray-200 resize-none focus:outline-none focus:border-indigo-600"
        spellCheck={false}
      />
    </div>
  )
}
