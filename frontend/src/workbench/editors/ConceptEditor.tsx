import { useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'
import { getProject, updateProjectMeta, actOnSuggestions } from '../../api/client'
import { useUiStore } from '../../store/uiSlice'
import { useWorkbenchStore } from '../../store/workbenchSlice'

const TEXT_FIELDS: [string, string][] = [
  ['title', 'Title'], ['genre', 'Genre'], ['category', 'Category'], ['language', 'Language'],
  ['logline', 'Logline'], ['tone', 'Tone'], ['target_audience', 'Target audience'],
]
const SUGGESTABLE = ['title', 'logline', 'description', 'num_chapters']

// B45: the concept as a first-class editable item — canonical meta fields plus the
// suggested_* proposals from generation (apply/dismiss per field; nothing auto-applies).
export default function ConceptEditor({ projectName }: { projectName: string }) {
  const [meta, setMeta] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const treeVersion = useWorkbenchStore(s => s.treeVersion)

  const load = () => getProject(projectName).then(setMeta).catch(() => {})
  useEffect(() => { load() }, [projectName, treeVersion])  // eslint-disable-line react-hooks/exhaustive-deps

  if (!meta) return <div className="text-sm text-gray-500">Loading…</div>

  const set = (k: string, v: any) => { setMeta({ ...meta, [k]: v }); useUiStore.getState().markDirty() }
  const save = async () => {
    setSaving(true)
    try {
      await updateProjectMeta(projectName, {
        title: meta.title, genre: meta.genre, category: meta.category, language: meta.language,
        logline: meta.logline, tone: meta.tone, target_audience: meta.target_audience,
        description: meta.description,
        num_chapters: meta.num_chapters,
        target_word_count: meta.target_word_count ?? null,
      })
      useUiStore.getState().markClean()
      bumpTree()
    } catch { alert('Save failed') }
    setSaving(false)
  }

  const suggestions = SUGGESTABLE
    .map(f => ({ field: f, value: meta[`suggested_${f}`] }))
    .filter(s => s.value !== null && s.value !== undefined && s.value !== '')

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Concept</h2>

      {suggestions.length > 0 && (
        <div className="border border-amber-800 bg-amber-900/20 rounded-lg p-3 space-y-2">
          <p className="text-xs text-amber-300">Generation suggested changes — nothing is applied until you accept it.</p>
          {suggestions.map(s => (
            <div key={s.field} className="flex items-start gap-2 text-xs">
              <span className="capitalize text-gray-400 w-28 shrink-0 pt-1">{s.field.replace(/_/g, ' ')}</span>
              <span className="flex-1 text-gray-200">{String(s.value)}</span>
              <button onClick={async () => { await actOnSuggestions(projectName, 'apply', [s.field]); load(); bumpTree() }}
                className="p-1.5 text-green-400 hover:text-green-300" title="Apply"><Check size={14} /></button>
              <button onClick={async () => { await actOnSuggestions(projectName, 'dismiss', [s.field]); load() }}
                className="p-1.5 text-gray-500 hover:text-red-400" title="Dismiss"><X size={14} /></button>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {TEXT_FIELDS.map(([f, label]) => (
          <label key={f} className={`block ${f === 'logline' ? 'sm:col-span-2' : ''}`}>
            <span className="text-xs text-gray-400">{label}</span>
            <input className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
              value={meta[f] ?? ''} onChange={e => set(f, e.target.value)} />
          </label>
        ))}
        <label className="block">
          <span className="text-xs text-gray-400">Chapters</span>
          <input type="number" min={1} className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={Array.isArray(meta.num_chapters) ? Math.max(...meta.num_chapters) : meta.num_chapters ?? ''}
            onChange={e => set('num_chapters', e.target.value ? parseInt(e.target.value) : '')} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Target word count</span>
          <input type="number" min={0} className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
            value={meta.target_word_count ?? ''}
            onChange={e => set('target_word_count', e.target.value ? parseInt(e.target.value) : null)} />
        </label>
      </div>
      <label className="block">
        <span className="text-xs text-gray-400">Description</span>
        <textarea className="w-full mt-1 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm h-32"
          value={meta.description ?? ''} onChange={e => set('description', e.target.value)} />
      </label>
      <button onClick={save} disabled={saving}
        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm disabled:opacity-50">
        {saving ? 'Saving…' : 'Save'}
      </button>
    </div>
  )
}
