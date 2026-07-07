import { useEffect, useState } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import BrainstormDrawer from './components/BrainstormDrawer'
import { Power, Menu, X } from 'lucide-react'
import HomePage from './pages/HomePage'
import NewProjectPage from './pages/NewProjectPage'
import ProjectDashboard from './pages/ProjectDashboard'
import ChapterEditorPage from './pages/ChapterEditorPage'
import LorebookPage from './pages/LorebookPage'
import OutlinePage from './pages/OutlinePage'
import WizardPage from './pages/WizardPage'
import SettingsPage from './pages/SettingsPage'
import { useUiStore } from './store/uiSlice'
import { shutdownApp } from './api/client'

export default function App() {
  const dirty = useUiStore(s => s.dirty)
  const [shutdownDone, setShutdownDone] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const projectMatch = location.pathname.match(/^\/projects\/([^/]+)/)
  const projectName = projectMatch && projectMatch[1] !== 'new' ? decodeURIComponent(projectMatch[1]) : null

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
      <nav className="border-b border-gray-800 px-4 sm:px-6 py-3">
        <div className="flex items-center gap-4 sm:gap-6">
          <Link to="/" onClick={() => setMenuOpen(false)} className="text-xl font-bold text-indigo-400">LibriScribe</Link>
          {/* Desktop links */}
          <Link to="/" className="hidden sm:inline text-gray-400 hover:text-gray-200 text-sm">Projects</Link>
          <Link to="/settings" className="hidden sm:inline text-gray-400 hover:text-gray-200 text-sm ml-auto">Settings</Link>
          {dirty && <span className="hidden sm:inline text-xs text-yellow-500">Unsaved changes</span>}
          <button
            onClick={handleQuit}
            title="Quit LibriScribe (stops the service)"
            className="hidden sm:flex items-center gap-1 text-gray-400 hover:text-red-400 text-sm"
          >
            <Power size={14} /> Quit
          </button>
          {/* Mobile hamburger */}
          <div className="sm:hidden ml-auto flex items-center gap-3">
            {dirty && <span className="text-xs text-yellow-500">Unsaved</span>}
            <button
              onClick={() => setMenuOpen(o => !o)}
              aria-label="Menu"
              aria-expanded={menuOpen}
              className="text-gray-300 hover:text-white p-1 -mr-1"
            >
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
        {/* Mobile dropdown menu */}
        {menuOpen && (
          <div className="sm:hidden mt-3 flex flex-col gap-1">
            <Link to="/" onClick={() => setMenuOpen(false)} className="px-2 py-2.5 rounded-lg hover:bg-gray-800 text-gray-300 text-sm">Projects</Link>
            <Link to="/settings" onClick={() => setMenuOpen(false)} className="px-2 py-2.5 rounded-lg hover:bg-gray-800 text-gray-300 text-sm">Settings</Link>
            <button
              onClick={() => { setMenuOpen(false); handleQuit() }}
              className="flex items-center gap-2 px-2 py-2.5 rounded-lg hover:bg-gray-800 text-gray-300 text-sm text-left"
            >
              <Power size={14} /> Quit LibriScribe
            </button>
          </div>
        )}
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-5 sm:py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:name" element={<ProjectDashboard />} />
          <Route path="/projects/:name/chapters/:n" element={<ChapterEditorPage />} />
          <Route path="/projects/:name/lorebook" element={<LorebookPage />} />
          <Route path="/projects/:name/lorebook/*" element={<LorebookPage />} />
          <Route path="/projects/:name/outline" element={<OutlinePage />} />
          <Route path="/projects/:name/wizard" element={<WizardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
      {projectName && <BrainstormDrawer key={projectName} projectName={projectName} />}
    </div>
  )
}
