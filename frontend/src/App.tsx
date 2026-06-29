import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Power } from 'lucide-react'
import HomePage from './pages/HomePage'
import NewProjectPage from './pages/NewProjectPage'
import ProjectDashboard from './pages/ProjectDashboard'
import ChapterEditorPage from './pages/ChapterEditorPage'
import LorebookPage from './pages/LorebookPage'
import OutlinePage from './pages/OutlinePage'
import SettingsPage from './pages/SettingsPage'
import { useUiStore } from './store/uiSlice'
import { shutdownApp } from './api/client'

export default function App() {
  const dirty = useUiStore(s => s.dirty)
  const [shutdownDone, setShutdownDone] = useState(false)

  // Best-effort guard against a hard browser/tab close with unsaved changes.
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (useUiStore.getState().dirty) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [])

  async function handleQuit() {
    if (
      useUiStore.getState().dirty &&
      !window.confirm(
        'You have unsaved changes. Quit LibriScribe anyway? Unsaved work will be lost.'
      )
    ) {
      return
    }
    try {
      await shutdownApp()
    } catch {
      // The server may close the connection before responding — that's expected.
    }
    setShutdownDone(true)
  }

  if (shutdownDone) {
    return (
      <div className="min-h-screen flex items-center justify-center text-center px-6">
        <div>
          <h1 className="text-2xl font-bold text-indigo-400 mb-2">LibriScribe has shut down</h1>
          <p className="text-gray-400">You can safely close this tab.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <a href="/" className="text-xl font-bold text-indigo-400">LibriScribe</a>
        <a href="/" className="text-gray-400 hover:text-gray-200 text-sm">Projects</a>
        <a href="/settings" className="text-gray-400 hover:text-gray-200 text-sm ml-auto">Settings</a>
        {dirty && <span className="text-xs text-yellow-500">Unsaved changes</span>}
        <button
          onClick={handleQuit}
          title="Quit LibriScribe (stops the service)"
          className="flex items-center gap-1 text-gray-400 hover:text-red-400 text-sm"
        >
          <Power size={14} /> Quit
        </button>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:name" element={<ProjectDashboard />} />
          <Route path="/projects/:name/chapters/:n" element={<ChapterEditorPage />} />
          <Route path="/projects/:name/lorebook" element={<LorebookPage />} />
          <Route path="/projects/:name/lorebook/*" element={<LorebookPage />} />
          <Route path="/projects/:name/outline" element={<OutlinePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
