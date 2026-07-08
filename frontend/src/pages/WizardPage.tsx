import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getWizardQuestions, generateWizardQuestions, saveWizardQuestions, elaborateWizard } from '../api/client'
import { Sparkles, Loader2, Save, Plus, Trash2, ArrowRight, ArrowLeft } from 'lucide-react'

// B38: gather the author's SPECIFICS via tailored questions, then elaborate the answers into
// staged lore candidates (sandbox cherry-pick). The answers are authoritative — never invented over.
export default function WizardPage() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const [qa, setQa] = useState<[string, string][]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [elaborating, setElaborating] = useState(false)
  const [info, setInfo] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!name) return
    getWizardQuestions(name)
      .then(r => setQa(Object.entries(r.questions || {})))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [name])

  const persist = async (entries: [string, string][]) => {
    if (!name) return
    setSaving(true)
    try { await saveWizardQuestions(name, Object.fromEntries(entries.filter(([q]) => q.trim()))) }
    catch { setInfo('Save failed') }
    finally { setSaving(false) }
  }

  const genQuestions = async () => {
    if (!name) return
    setGenerating(true); setInfo('')
    try {
      const r = await generateWizardQuestions(name)
      setQa(Object.entries(r.questions || {}))
      setInfo('Questions tailored to your project. Edit or remove any, answer the ones you care about.')
    } catch (e: any) { setInfo(e?.response?.data?.detail || 'Question generation failed') }
    finally { setGenerating(false) }
  }

  const elaborate = async () => {
    if (!name) return
    await persist(qa)
    setElaborating(true); setInfo(''); setError('')
    try {
      const run = await elaborateWizard(name)
      setInfo(`Created ${run.candidates?.length ?? 0} staged candidates.`)
      navigate(`/projects/${name}/lorebook`, { state: { tab: 'Sandbox' } })  // land on the run
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Elaboration failed — your answers are saved; try again.')
    }
    finally { setElaborating(false) }
  }

  const answered = qa.filter(([, a]) => a.trim()).length

  if (loading) return <div className="text-gray-400">Loading…</div>

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/projects/${name}`} className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"><ArrowLeft size={12} /> {name}</Link>
          <h1 className="text-2xl font-bold mt-1">Story Wizard</h1>
          <p className="text-sm text-gray-400 mt-1">
            Answer questions about <i>your</i> story — how many main characters, the arcs, the setting.
            The AI elaborates <b>your answers</b> into lorebook entries (staged for your review — nothing
            is added without your approval). Your answers are authoritative; it never invents over them.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button onClick={genQuestions} disabled={generating} className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm disabled:opacity-50">
          {generating ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
          {qa.length ? 'Regenerate questions (AI)' : 'Generate questions (AI)'}
        </button>
        <button onClick={() => setQa([...qa, ['', '']])} className="flex items-center gap-1 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm"><Plus size={14} /> Add my own</button>
        {qa.length > 0 && (
          <button onClick={() => persist(qa)} disabled={saving} className="flex items-center gap-1 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm disabled:opacity-50">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
          </button>
        )}
      </div>
      {info && <div className="text-xs text-gray-400">{info}</div>}
      {error && <div className="px-3 py-2 bg-red-900/30 border border-red-800 rounded-lg text-xs text-red-300">{error}</div>}

      <div className="space-y-3">
        {qa.map(([q, a], i) => (
          <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-3 space-y-1.5">
            <div className="flex items-start gap-2">
              <input value={q} placeholder="Your question…"
                onChange={e => setQa(qa.map((p, idx) => idx === i ? [e.target.value, p[1]] : p))}
                className="flex-1 bg-transparent text-sm font-medium outline-none border-b border-transparent focus:border-gray-600" />
              <button onClick={() => setQa(qa.filter((_, idx) => idx !== i))} className="text-gray-600 hover:text-red-400 p-1"><Trash2 size={13} /></button>
            </div>
            <textarea rows={2} value={a} placeholder="Your answer (leave blank to skip)…"
              onChange={e => setQa(qa.map((p, idx) => idx === i ? [p[0], e.target.value] : p))}
              onBlur={() => persist(qa)}
              className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm resize-y" />
          </div>
        ))}
        {qa.length === 0 && (
          <p className="text-gray-500 text-sm py-8 text-center">
            Click <b>Generate questions</b> to get questions tailored to your project — or add your own.
          </p>
        )}
      </div>

      {qa.length > 0 && (
        <div className="flex items-center gap-3 pt-2">
          <button onClick={elaborate} disabled={elaborating || answered === 0}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-medium disabled:opacity-50"
            title="Extract + enrich lore entries from your answers; staged in the Sandbox for your review">
            {elaborating ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
            {elaborating ? 'Elaborating…' : `Create lore from ${answered} answer${answered === 1 ? '' : 's'}`}
          </button>
          <span className="text-xs text-gray-500">Results land in Lorebook → Sandbox for cherry-pick.</span>
        </div>
      )}
    </div>
  )
}
