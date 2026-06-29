import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import NewProjectPage from './pages/NewProjectPage'
import ProjectDashboard from './pages/ProjectDashboard'
import ChapterEditorPage from './pages/ChapterEditorPage'
import LorebookPage from './pages/LorebookPage'
import OutlinePage from './pages/OutlinePage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <a href="/" className="text-xl font-bold text-indigo-400">LibriScribe</a>
        <a href="/" className="text-gray-400 hover:text-gray-200 text-sm">Projects</a>
        <a href="/settings" className="text-gray-400 hover:text-gray-200 text-sm ml-auto">Settings</a>
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
