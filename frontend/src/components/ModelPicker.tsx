import { Loader2, RefreshCw } from 'lucide-react'

export interface ModelInfo { id: string; label?: string; free?: boolean }

// A model field with a real dropdown. The text input allows any custom id; clicking Load
// fetches the provider's models and shows them in a proper <select> (an HTML <datalist>
// only surfaces options that match the already-typed text, so it reads as "no dropdown").
export default function ModelPicker({
  value, onChange, models, loading, onLoad, placeholder,
}: {
  value: string
  onChange: (v: string) => void
  models: ModelInfo[]
  loading: boolean
  onLoad: () => void
  placeholder?: string
}) {
  const inList = models.some(m => m.id === value)
  const freeCount = models.filter(m => m.free).length
  return (
    <div>
      <div className="flex gap-2 mt-1">
        <input
          className="flex-1 min-w-0 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder || 'Type a model id, or Load to choose from a list'}
        />
        <button
          onClick={onLoad}
          disabled={loading}
          title="Fetch available models from the provider/server"
          className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />} Load
        </button>
      </div>
      {models.length > 0 && (
        <select
          className="w-full mt-2 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
          value={inList ? value : ''}
          onChange={e => { if (e.target.value) onChange(e.target.value) }}
        >
          <option value="">
            — choose from {models.length} loaded model{models.length === 1 ? '' : 's'}
            {freeCount > 0 ? ` (${freeCount} free)` : ''} —
          </option>
          {models.map(m => (
            <option key={m.id} value={m.id}>{m.label || m.id}{m.free ? ' — free' : ''}</option>
          ))}
        </select>
      )}
    </div>
  )
}
