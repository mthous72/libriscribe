import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../api/client'

const CATEGORIES = ['Fiction', 'Non-Fiction', 'Business', 'Research Paper']
const LENGTHS = ['Short Story', 'Novella', 'Novel']
const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'claude', label: 'Claude' },
  { value: 'google_ai_studio', label: 'Google AI Studio' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'local', label: 'Local (OpenAI-compatible)' },
]
const REVIEW_PREFS = ['AI', 'Human']

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    project_name: '',
    title: '',
    genre: '',
    description: '',
    category: 'Fiction',
    language: 'English',
    num_characters: 3,
    worldbuilding_needed: true,
    review_preference: 'AI',
    book_length: 'Novel',
    tone: 'Engaging',
    target_audience: 'General',
    num_chapters: 10,
    llm_provider: 'openai',
    model: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const update = (field: string, value: any) => setForm({ ...form, [field]: value })

  const submit = async () => {
    setSubmitting(true)
    try {
      const data = { ...form }
      if (!data.project_name) data.project_name = data.title.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 40)
      await createProject(data)
      navigate(`/projects/${data.project_name}`)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  const steps = [
    // Step 0: Basic Info
    <div key={0} className="space-y-4">
      <h2 className="text-xl font-semibold">Basic Info</h2>
      <label className="block">
        <span className="text-sm text-gray-400">Title</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.title} onChange={e => update('title', e.target.value)} placeholder="My Amazing Novel" />
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Project Name (slug)</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.project_name} onChange={e => update('project_name', e.target.value)} placeholder="auto-generated from title" />
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Genre</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.genre} onChange={e => update('genre', e.target.value)} placeholder="Fantasy, Sci-Fi, Romance..." />
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Description</span>
        <textarea className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg h-24" value={form.description} onChange={e => update('description', e.target.value)} placeholder="Describe your story idea..." />
      </label>
    </div>,
    // Step 1: Category & Length
    <div key={1} className="space-y-4">
      <h2 className="text-xl font-semibold">Category & Length</h2>
      <label className="block">
        <span className="text-sm text-gray-400">Category</span>
        <select className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.category} onChange={e => update('category', e.target.value)}>
          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Book Length</span>
        <select className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.book_length} onChange={e => update('book_length', e.target.value)}>
          {LENGTHS.map(l => <option key={l}>{l}</option>)}
        </select>
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Language</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.language} onChange={e => update('language', e.target.value)} />
      </label>
    </div>,
    // Step 2: Characters & World
    <div key={2} className="space-y-4">
      <h2 className="text-xl font-semibold">Characters & World</h2>
      <label className="block">
        <span className="text-sm text-gray-400">Number of Characters</span>
        <input type="number" className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.num_characters} onChange={e => update('num_characters', parseInt(e.target.value) || 0)} />
      </label>
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={form.worldbuilding_needed} onChange={e => update('worldbuilding_needed', e.target.checked)} className="rounded" />
        <span className="text-sm text-gray-400">Worldbuilding needed</span>
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Number of Chapters</span>
        <input type="number" className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.num_chapters} onChange={e => update('num_chapters', parseInt(e.target.value) || 1)} />
      </label>
    </div>,
    // Step 3: Tone & Audience
    <div key={3} className="space-y-4">
      <h2 className="text-xl font-semibold">Tone & Audience</h2>
      <label className="block">
        <span className="text-sm text-gray-400">Tone</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.tone} onChange={e => update('tone', e.target.value)} />
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Target Audience</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.target_audience} onChange={e => update('target_audience', e.target.value)} />
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Review Preference</span>
        <select className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.review_preference} onChange={e => update('review_preference', e.target.value)}>
          {REVIEW_PREFS.map(r => <option key={r}>{r}</option>)}
        </select>
      </label>
    </div>,
    // Step 4: LLM Config
    <div key={4} className="space-y-4">
      <h2 className="text-xl font-semibold">LLM Configuration</h2>
      <label className="block">
        <span className="text-sm text-gray-400">LLM Provider</span>
        <select className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.llm_provider} onChange={e => update('llm_provider', e.target.value)}>
          {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </label>
      <label className="block">
        <span className="text-sm text-gray-400">Model (optional, leave blank for the provider default)</span>
        <input className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" value={form.model} onChange={e => update('model', e.target.value)} placeholder="e.g. gpt-4o, claude-3-opus, or a local model id" />
        {form.llm_provider === 'local' && (
          <span className="text-xs text-emerald-400/80">
            Uses your Local provider from Settings (base URL). Set a model id here or as the
            Local model in Settings — requests stay on your machine.
          </span>
        )}
      </label>
    </div>,
  ]

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Create New Project</h1>

      {/* Step indicators */}
      <div className="flex gap-2 mb-6">
        {steps.map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded ${i <= step ? 'bg-indigo-500' : 'bg-gray-800'}`} />
        ))}
      </div>

      {steps[step]}

      <div className="flex justify-between mt-8">
        <button
          onClick={() => step > 0 ? setStep(step - 1) : navigate('/')}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm"
        >
          {step > 0 ? 'Back' : 'Cancel'}
        </button>
        {step < steps.length - 1 ? (
          <button
            onClick={() => setStep(step + 1)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm"
          >
            Next
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={submitting || !form.title}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create Project'}
          </button>
        )}
      </div>
    </div>
  )
}
