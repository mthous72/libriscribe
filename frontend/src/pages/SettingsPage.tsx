import { useEffect, useState } from 'react'
import { getSettings, updateSettings, getProviders } from '../api/client'
import { Save, Check, X } from 'lucide-react'

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({})
  const [providers, setProviders] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

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
      // Refresh providers
      getProviders().then(setProviders).catch(() => {})
    } catch (e) {
      alert('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const fields = [
    { key: 'openai_api_key', label: 'OpenAI API Key', type: 'password' },
    { key: 'openai_model', label: 'OpenAI Model' },
    { key: 'claude_api_key', label: 'Claude API Key', type: 'password' },
    { key: 'claude_model', label: 'Claude Model' },
    { key: 'google_ai_studio_api_key', label: 'Google AI Studio API Key', type: 'password' },
    { key: 'google_ai_studio_model', label: 'Google AI Studio Model' },
    { key: 'deepseek_api_key', label: 'DeepSeek API Key', type: 'password' },
    { key: 'deepseek_model', label: 'DeepSeek Model' },
    { key: 'mistral_api_key', label: 'Mistral API Key', type: 'password' },
    { key: 'mistral_model', label: 'Mistral Model' },
    { key: 'openrouter_api_key', label: 'OpenRouter API Key', type: 'password' },
    { key: 'openrouter_model', label: 'OpenRouter Model' },
    { key: 'default_llm', label: 'Default LLM Provider' },
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Provider Status */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h2 className="text-sm font-medium text-gray-400 mb-3">Provider Status</h2>
        <div className="grid grid-cols-3 gap-2">
          {providers.map((p: any) => (
            <div key={p.name} className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg text-sm">
              {p.configured ? <Check size={14} className="text-green-400" /> : <X size={14} className="text-gray-600" />}
              <span className={p.configured ? 'text-gray-200' : 'text-gray-500'}>{p.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* API Keys */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-medium text-gray-400 mb-2">API Configuration</h2>
        {fields.map(f => (
          <label key={f.key} className="block">
            <span className="text-xs text-gray-400">{f.label}</span>
            <input
              type={f.type || 'text'}
              className="w-full mt-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
              value={settings[f.key] || ''}
              onChange={e => setSettings({ ...settings, [f.key]: e.target.value })}
            />
          </label>
        ))}

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          <Save size={14} /> {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
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
