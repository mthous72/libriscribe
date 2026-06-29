import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProject } from '../hooks/useProject'
import { useWebSocket } from '../hooks/useWebSocket'
import { useGenerationStore } from '../store/generationSlice'
import { startGeneration, cancelGeneration, resumeGeneration, listChapters, getCost } from '../api/client'
import { Play, Square, BookOpen, Map, FileText, Download } from 'lucide-react'

const STAGES = ['concept', 'outline', 'characters', 'worldbuilding', 'chapters', 'formatting']

export default function ProjectDashboard() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const { project, progress, loading, refresh } = useProject(name)
  const { sendMessage } = useWebSocket(name)
  const { jobStatus, logs, streamBuffer, stageStatuses, pendingReview, reset } = useGenerationStore()
  const [chapters, setChapters] = useState<any[]>([])
  const [cost, setCost] = useState<any>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { reset() }, [name])

  useEffect(() => {
    if (name) {
      listChapters(name).then(setChapters).catch(() => {})
      getCost(name).then(setCost).catch(() => {})
    }
  }, [name, jobStatus])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  if (loading) return <div className="text-gray-400">Loading...</div>
  if (!project) return <div className="text-red-400">Project not found</div>

  const handleStart = async () => {
    try {
      await startGeneration(name!, { streaming: true })
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to start')
    }
  }

  const handleCancel = async () => {
    try {
      await cancelGeneration(name!)
    } catch {}
  }

  const handleReviewDecision = async (proceed: boolean, applyStyle: boolean) => {
    try {
      await resumeGeneration(name!, { proceed, apply_ai_style: applyStyle })
    } catch {}
  }

  const isRunning = jobStatus === 'running'
  const isPaused = jobStatus === 'paused_for_review'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{project.title}</h1>
          <p className="text-gray-400 text-sm">{project.genre} &middot; {project.category} &middot; {project.language}</p>
          {project.logline && <p className="text-gray-500 text-sm mt-1 italic">{project.logline}</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={() => navigate(`/projects/${name}/lorebook`)} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-1"><BookOpen size={14} /> Lorebook</button>
          <button onClick={() => navigate(`/projects/${name}/outline`)} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-1"><Map size={14} /> Outline</button>
        </div>
      </div>

      {/* Pipeline Stages */}
      <div className="grid grid-cols-6 gap-2">
        {STAGES.map(stage => {
          const status = stageStatuses[stage] || progress?.stage_statuses?.[stage] || 'pending'
          const colors: Record<string, string> = {
            complete: 'bg-green-900 border-green-700 text-green-300',
            in_progress: 'bg-indigo-900 border-indigo-700 text-indigo-300 animate-pulse',
            failed: 'bg-red-900 border-red-700 text-red-300',
            skipped: 'bg-gray-800 border-gray-700 text-gray-500',
            pending: 'bg-gray-900 border-gray-800 text-gray-500',
          }
          return (
            <div key={stage} className={`border rounded-lg p-3 text-center text-xs font-medium capitalize ${colors[status] || colors.pending}`}>
              {stage}
              <div className="text-[10px] mt-1 opacity-75">{status}</div>
            </div>
          )
        })}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {!isRunning && !isPaused && (
          <button onClick={handleStart} className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-medium">
            <Play size={16} /> Start Generation
          </button>
        )}
        {isRunning && (
          <button onClick={handleCancel} className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-medium">
            <Square size={16} /> Cancel
          </button>
        )}
        {cost && (
          <span className="text-xs text-gray-500">Session cost: ${cost.total_cost?.toFixed(4) || '0.0000'}</span>
        )}
        <span className="text-xs text-gray-600">Status: {jobStatus}</span>
      </div>

      {/* Human Review Modal */}
      {isPaused && pendingReview && (
        <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-5">
          <h3 className="font-semibold text-yellow-300 mb-2">Human Review Required</h3>
          <p className="text-sm text-gray-300 mb-4">{pendingReview.message}</p>
          <div className="flex gap-3">
            <button onClick={() => handleReviewDecision(true, false)} className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm">Proceed</button>
            <button onClick={() => handleReviewDecision(true, true)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm">Apply AI Style</button>
          </div>
        </div>
      )}

      {/* Streaming Panel */}
      {streamBuffer && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Live Stream</h3>
          <div className="prose prose-invert max-w-none text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
            {streamBuffer}
          </div>
        </div>
      )}

      {/* Log Feed */}
      {logs.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Log ({logs.length})</h3>
          <div className="font-mono text-xs text-gray-400 max-h-48 overflow-y-auto space-y-0.5">
            {logs.map((log, i) => <div key={i}>{log}</div>)}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {/* Chapters */}
      {chapters.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Chapters</h3>
          <div className="space-y-1">
            {chapters.map(ch => (
              <div
                key={ch.chapter_number}
                onClick={() => ch.has_content && navigate(`/projects/${name}/chapters/${ch.chapter_number}`)}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm ${ch.has_content ? 'hover:bg-gray-800 cursor-pointer' : 'opacity-50'}`}
              >
                <div className="flex items-center gap-2">
                  <FileText size={14} className={ch.has_content ? 'text-green-400' : 'text-gray-600'} />
                  <span>Ch. {ch.chapter_number}: {ch.title || 'Untitled'}</span>
                </div>
                <span className="text-gray-500 text-xs">{ch.word_count > 0 ? `${ch.word_count} words` : '-'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Downloads */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Downloads</h3>
        <div className="flex gap-3">
          <a href={`/api/projects/${name}/download/manuscript.md`} target="_blank" rel="noopener" className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-1">
            <Download size={14} /> manuscript.md
          </a>
          <a href={`/api/projects/${name}/download/manuscript_original.md`} target="_blank" rel="noopener" className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-1">
            <Download size={14} /> original.md
          </a>
        </div>
      </div>
    </div>
  )
}
