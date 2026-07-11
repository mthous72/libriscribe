import { useState } from 'react'
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { useGenerationStore } from '../store/generationSlice'

// B45: slim live-activity strip at the bottom of the center pane. Reads the existing
// generation store (WS events) unchanged; expands to show the stream tail + recent logs.
export default function GenerationStrip() {
  const jobStatus = useGenerationStore(s => s.jobStatus)
  const logs = useGenerationStore(s => s.logs)
  const streamBuffer = useGenerationStore(s => s.streamBuffer)
  const [open, setOpen] = useState(false)

  const running = jobStatus === 'running'
  if (!running && logs.length === 0) return null

  const lastLog = logs[logs.length - 1]
  return (
    <div className="mt-4 border border-gray-800 rounded-lg bg-gray-900/80">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:text-gray-200">
        {running
          ? <Loader2 size={13} className="animate-spin text-indigo-400 shrink-0" />
          : <span className={`shrink-0 w-2 h-2 rounded-full ${jobStatus === 'failed' ? 'bg-red-500' : 'bg-green-500'}`} />}
        <span className="truncate flex-1 text-left">
          {running ? 'Generating…' : `Last run: ${jobStatus}`}{lastLog ? ` — ${lastLog}` : ''}
        </span>
        {open ? <ChevronDown size={14} className="shrink-0" /> : <ChevronUp size={14} className="shrink-0" />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {streamBuffer && (
            <pre className="max-h-48 overflow-y-auto text-[11px] text-gray-300 whitespace-pre-wrap bg-gray-950 border border-gray-800 rounded p-2">
              {streamBuffer.slice(-4000)}
            </pre>
          )}
          <div className="max-h-32 overflow-y-auto space-y-0.5">
            {logs.slice(-15).map((l, i) => (
              <div key={i} className="text-[11px] text-gray-500">{l}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
