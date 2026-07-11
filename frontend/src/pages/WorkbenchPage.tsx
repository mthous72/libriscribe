import { useEffect, useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Sparkles, BookOpen, SlidersHorizontal } from 'lucide-react'
import { getWorkbenchTree, type WorkbenchTree } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import { useWorkbenchStore, NodeRef, parseNodeRef, serializeNodeRef, sameNodeRef } from '../store/workbenchSlice'
import { useBrainstormStore } from '../store/brainstormSlice'
import { useUiStore } from '../store/uiSlice'
import WorkbenchLayout from '../workbench/WorkbenchLayout'
import StoryTree from '../workbench/StoryTree'
import ItemEditorHost from '../workbench/ItemEditorHost'
import BrainstormPane from '../workbench/BrainstormPane'

export default function WorkbenchPage() {
  const { name } = useParams<{ name: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tree, setTree] = useState<WorkbenchTree | null>(null)
  const [error, setError] = useState('')
  const selection = useWorkbenchStore(s => s.selection)
  const setSelection = useWorkbenchStore(s => s.setSelection)
  const treeVersion = useWorkbenchStore(s => s.treeVersion)
  const bumpTree = useWorkbenchStore(s => s.bumpTree)
  const loreVersion = useBrainstormStore(s => s.loreVersion)

  useWebSocket(name || '')

  // Selection ← URL (deep links / back button)
  useEffect(() => {
    const fromUrl = parseNodeRef(searchParams.get('sel'))
    if (fromUrl && !sameNodeRef(fromUrl, useWorkbenchStore.getState().selection)) {
      setSelection(fromUrl)
    }
  }, [searchParams])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!name) return
    getWorkbenchTree(name).then(t => { setTree(t); setError('') })
      .catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load the project'))
  }, [name, treeVersion, loreVersion])

  const select = (ref: NodeRef) => {
    // Editing an earlier item never changes later content — but switching items with unsaved
    // edits would lose them; same guard the rest of the app uses.
    if (useUiStore.getState().dirty &&
        !confirm('You have unsaved changes on this item. Switch anyway? Unsaved edits are lost.')) {
      return
    }
    useUiStore.getState().markClean()
    setSelection(ref)
    setSearchParams({ sel: serializeNodeRef(ref) }, { replace: false })
  }

  if (!name) return null
  if (error) return <div className="text-sm text-red-400">{error}</div>
  if (!tree) return <div className="text-sm text-gray-500">Loading workbench…</div>

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/" className="text-gray-400 hover:text-gray-200 p-1.5 -m-1.5" title="All projects">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold truncate">{name}</h1>
        <span className="hidden sm:inline text-xs text-gray-500">work the story one item at a time</span>
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          <Link to={`/projects/${name}/wizard`} title="Answer questions about your story; the AI elaborates them into staged lore"
            className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300">
            <Sparkles size={13} /> Wizard
          </Link>
          <Link to={`/projects/${name}/lorebook`} title="Lore tools: import, sandbox review, gap scans, references, graph"
            className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300">
            <BookOpen size={13} /> Lore tools
          </Link>
          <Link to={`/projects/${name}/automation`} title="Batch generation, exports, versions, and model settings"
            className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300">
            <SlidersHorizontal size={13} /> Automation
          </Link>
          <button onClick={bumpTree} title="Refresh from the project"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>
      <WorkbenchLayout
        left={<StoryTree tree={tree} selection={selection} onSelect={select} />}
        center={<ItemEditorHost projectName={name} tree={tree} selection={selection} onSelect={select} />}
        right={<BrainstormPane projectName={name} />}
      />
    </div>
  )
}
