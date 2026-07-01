import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProjects, deleteProject, importProject } from '../api/client'
import { Plus, Trash2, BookOpen, Upload } from 'lucide-react'

export default function HomePage() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const onImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const bundle = JSON.parse(await file.text())
      const res = await importProject({ bundle })
      if (res.renamed) alert(`Imported as "${res.project_name}" — a project named "${res.requested_name}" already existed.`)
      navigate(`/projects/${res.project_name}`)
    } catch (err: any) {
      if (err instanceof SyntaxError) alert('That file is not valid JSON.')
      else alert(err?.response?.data?.detail || 'Import failed')
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const load = async () => {
    try {
      setProjects(await listProjects())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete project "${name}"?`)) return
    await deleteProject(name)
    load()
  }

  if (loading) return <div className="text-gray-400">Loading projects...</div>

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            title="Import a project from a .libriscribe.json bundle"
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            <Upload size={16} /> {importing ? 'Importing…' : 'Import Project'}
          </button>
          <input ref={fileRef} type="file" accept="application/json,.json,.libriscribe.json" className="hidden" onChange={onImport} />
          <button
            onClick={() => navigate('/projects/new')}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium"
          >
            <Plus size={16} /> New Project
          </button>
        </div>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <BookOpen size={48} className="mx-auto mb-4 opacity-50" />
          <p>No projects yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <div
              key={p.project_name}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-indigo-600 cursor-pointer transition-colors"
              onClick={() => navigate(`/projects/${p.project_name}`)}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg">{p.title}</h3>
                  <p className="text-gray-400 text-sm">{p.genre} &middot; {p.category}</p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(p.project_name) }}
                  className="text-gray-600 hover:text-red-400 p-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
                <span className="px-2 py-0.5 bg-gray-800 rounded">{p.next_step}</span>
                <span>{p.chapter_count}/{p.total_chapters} chapters</span>
                <span>{p.language}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
