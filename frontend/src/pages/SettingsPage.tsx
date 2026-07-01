import { useEffect, useState } from 'react'
import { getSettings, updateSettings, getProviders, fetchProviderModels } from '../api/client'
import ModelPicker from '../components/ModelPicker'
import { Save, Check, X, Loader2, RefreshCw } from 'lucide-react'

const PROVIDERS = [
  { key: 'openai', label: 'OpenAI' },
  { key: 'claude', label: 'Claude' },
  { key: 'google_ai_studio', label: 'Google AI Studio' },
  { key: 'deepseek', label: 'DeepSeek' },
  { key: 'mistral', label: 'Mistral' },
  { key: 'openrouter', label: 'OpenRouter' },
  { key: 'local', label: 'Local (OpenAI-compatible)' },
]

// OpenAI-compatible servers serve the API under /v1. If the user pastes a bare
// host:port, append /v1 so the endpoints resolve.
function normalizeBaseUrl(url: string): string {
  const u = (url || '').trim().replace(/\/+$/, '')
  if (!u) return u
  try {
    const p = new URL(u)
    if (p.pathname === '' || p.pathname === '/') return `${u}/v1`
  } catch {
    return u
  }
  return u
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({})
  const [providers, setProviders] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [models, setModels] = useState<Record<string, any[]>>({})
  const [loadingModels, setLoadingModels] = useState<string | null>(null)
  const [embModels, setEmbModels] = useState<any[]>([])
  const [loadingEmb, setLoadingEmb] = useState(false)
  const [hiddenProviders, setHiddenProviders] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(localStorage.getItem('libriscribe:hidden-providers') || '[]')) } catch { return new Set() }
  })
  const toggleProvider = (key: string) => setHiddenProviders(prev => {
    const next = new Set(prev)
    if (next.has(key)) next.delete(key); else next.add(key)
    localStorage.setItem('libriscribe:hidden-providers', JSON.stringify([...next]))
    return next
  })

  useEffect(() => {
    getSettings().then(setSettings).catch(() => {})
    getProviders().then(setProviders).catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateSettings(settings)
      setSettings(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      getProviders().then(setProviders).catch(() => {})
    } catch (e) {
      alert('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  async function loadModels(provider: string) {
    // Only send a freshly-typed key; masked values ("abcd...wxyz") fall back to
    // the saved key on the server.
    const entered = settings[`${provider}_api_key`]
    const api_key = entered && !entered.includes('...') ? entered : undefined
    let base_url = settings[`${provider}_base_url`] || undefined
    if (provider === 'local' && base_url) base_url = normalizeBaseUrl(base_url)
    setLoadingModels(provider)
    try {
      const list = await fetchProviderModels({ provider, api_key, base_url })
      setModels(m => ({ ...m, [provider]: list }))
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to load models')
    } finally {
      setLoadingModels(null)
    }
  }

  // Embedding models come from the same /models listing as chat models; we just surface
  // the likely-embedding ones first (the endpoint returns everything the provider serves).
  const isEmbeddingId = (id: string) => /embed|bge|e5|gte|minilm|nomic|instructor/i.test(id)

  async function loadEmbeddingModels() {
    const source = settings.retrieval_embedding_provider
    if (source !== 'openai' && source !== 'local') return
    const provider = source === 'openai' ? 'openai' : 'local'
    const entered = provider === 'openai' ? settings.openai_api_key : settings.local_api_key
    const api_key = entered && !entered.includes('...') ? entered : undefined
    let base_url = provider === 'local' ? (settings.local_base_url || undefined) : undefined
    if (provider === 'local' && base_url) base_url = normalizeBaseUrl(base_url)
    setLoadingEmb(true)
    try {
      const list = await fetchProviderModels({ provider, api_key, base_url })
      list.sort((a: any, b: any) => (isEmbeddingId(b.id) ? 1 : 0) - (isEmbeddingId(a.id) ? 1 : 0))
      setEmbModels(list)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to load models')
    } finally {
      setLoadingEmb(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Provider Status */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-gray-400">Provider Status</h2>
          <span className="text-[11px] text-gray-600">Uncheck a provider to hide its section below</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {providers.map((p: any) => (
            <label key={p.name} className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg text-sm cursor-pointer" title="Show this provider in API Configuration">
              <input type="checkbox" checked={!hiddenProviders.has(p.name)} onChange={() => toggleProvider(p.name)} />
              {p.configured ? <Check size={14} className="text-green-400" /> : <X size={14} className="text-gray-600" />}
              <span className={p.configured ? 'text-gray-200' : 'text-gray-500'}>{p.name}</span>
            </label>
          ))}
        </div>
      </div>

      {/* API Keys + Models */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
        <h2 className="text-sm font-medium text-gray-400">API Configuration</h2>
        <p className="text-xs text-gray-500">
          Add a key to enable a provider. Click <span className="text-gray-300">Load</span> to
          fetch that provider's available models into the dropdown (works with a just-typed key
          before saving).
        </p>

        {PROVIDERS.filter(p => !hiddenProviders.has(p.key)).map(p => {
          const loaded = models[p.key]
          const freeCount = loaded ? loaded.filter((m: any) => m.free).length : 0
          return (
            <div key={p.key} className="space-y-2 border-b border-gray-800 pb-3 last:border-b-0">
              <span className="text-sm font-medium text-gray-300">{p.label}</span>

              {p.key === 'local' && (
                <>
                  <label className="block">
                    <span className="text-xs text-gray-400">Server Base URL</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      <input
                        className="flex-1 min-w-0 basis-full sm:basis-0 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
                        value={settings.local_base_url || ''}
                        onChange={e => setSettings({ ...settings, local_base_url: e.target.value })}
                        onBlur={e => {
                          const n = normalizeBaseUrl(e.target.value)
                          if (n !== (settings.local_base_url || '')) setSettings({ ...settings, local_base_url: n })
                        }}
                        placeholder="http://localhost:1234/v1"
                      />
                      <button
                        onClick={() => setSettings({ ...settings, local_base_url: 'http://localhost:1234/v1' })}
                        className="px-2 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs whitespace-nowrap"
                      >LM Studio</button>
                      <button
                        onClick={() => setSettings({ ...settings, local_base_url: 'http://localhost:11434/v1' })}
                        className="px-2 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs whitespace-nowrap"
                      >Ollama</button>
                    </div>
                  </label>
                  <p className="text-xs text-emerald-400/80">
                    Requests go only to this address — nothing leaves your machine. For fully
                    offline use, don't add cloud providers to this provider's fallback chain.
                  </p>
                </>
              )}

              <label className="block">
                <span className="text-xs text-gray-400">
                  API Key{p.key === 'local' ? ' (optional)' : ''}
                </span>
                <input
                  type="password"
                  className="w-full mt-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
                  value={settings[`${p.key}_api_key`] || ''}
                  onChange={e => setSettings({ ...settings, [`${p.key}_api_key`]: e.target.value })}
                />
              </label>

              <label className="block">
                <span className="text-xs text-gray-400">Model</span>
                <ModelPicker
                  value={settings[`${p.key}_model`] || ''}
                  onChange={v => setSettings({ ...settings, [`${p.key}_model`]: v })}
                  models={loaded || []}
                  loading={loadingModels === p.key}
                  onLoad={() => loadModels(p.key)}
                />
              </label>
            </div>
          )
        })}

        <label className="block">
          <span className="text-xs text-gray-400">Default LLM Provider</span>
          <select
            className="w-full mt-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
            value={settings.default_llm || 'openai'}
            onChange={e => setSettings({ ...settings, default_llm: e.target.value })}
          >
            {PROVIDERS.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
          </select>
        </label>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          <Save size={14} /> {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>

      {/* Embeddings (semantic search) */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-medium text-gray-400">Embeddings (semantic search)</h2>
        <p className="text-xs text-gray-500">
          Powers <span className="text-gray-300">Semantic</span> and <span className="text-gray-300">Hybrid</span> search
          modes (set per book on each project's dashboard). Choose where embeddings come from —
          a cloud provider or a local OpenAI-compatible server. Leave <span className="text-gray-300">Off</span> to
          use keyword search only.
        </p>
        <label className="block">
          <span className="text-xs text-gray-400">Embedding source</span>
          <select
            className="w-full mt-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
            value={settings.retrieval_embedding_provider || 'off'}
            onChange={e => setSettings({ ...settings, retrieval_embedding_provider: e.target.value })}
          >
            <option value="off">Off (keyword only)</option>
            <option value="openai">OpenAI (cloud)</option>
            <option value="local">Local (OpenAI-compatible server)</option>
          </select>
        </label>

        {(settings.retrieval_embedding_provider === 'openai' || settings.retrieval_embedding_provider === 'local') && (() => {
          const isLocal = settings.retrieval_embedding_provider === 'local'
          const field = isLocal ? 'retrieval_embedding_model' : 'openai_embedding_model'
          const embFree = embModels.filter((m: any) => isEmbeddingId(m.id)).length
          return (
            <label className="block">
              <span className="text-xs text-gray-400">Embedding model</span>
              <ModelPicker
                value={settings[field] || ''}
                onChange={v => setSettings({ ...settings, [field]: v })}
                models={embModels.map((m: any) => ({ id: m.id, label: (m.label || m.id) + (isEmbeddingId(m.id) ? ' — embedding' : ''), free: m.free }))}
                loading={loadingEmb}
                onLoad={loadEmbeddingModels}
                placeholder={isLocal ? 'nomic-embed-text' : 'text-embedding-3-small'}
              />
              {isLocal
                ? <p className="text-xs text-emerald-400/80">
                    Uses the Local server Base URL above — fully offline. Load a dedicated embedding
                    model in LM Studio / Ollama (e.g. <span className="text-gray-300">nomic-embed-text</span>),
                    then <span className="text-gray-300">Load</span> to pick its exact id.
                  </p>
                : <p className="text-xs text-gray-500">Uses your OpenAI API key from above.</p>}
            </label>
          )
        })()}

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          <Save size={14} /> {saving ? 'Saving...' : saved ? 'Saved!' : 'Save'}
        </button>
      </div>

      {/* Writing System Prompt */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-medium text-gray-400 mb-2">Writing System Prompt</h2>
        <p className="text-xs text-gray-500">
          Global system prompt injected into creative writing LLM calls. Per-project overrides can be set in project settings.
        </p>
        <textarea
          className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm h-40 font-mono resize-y"
          placeholder="Leave empty to use the built-in default creative writing system prompt..."
          value={settings.writing_system_prompt || ''}
          onChange={e => setSettings({ ...settings, writing_system_prompt: e.target.value })}
        />
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          <Save size={14} /> {saving ? 'Saving...' : saved ? 'Saved!' : 'Save'}
        </button>
      </div>
    </div>
  )
}
