import { useEffect } from 'react'
import { Link2, Link2Off } from 'lucide-react'
import BrainstormPanel from '../components/BrainstormPanel'
import { useBrainstormStore, BrainstormFocus } from '../store/brainstormSlice'
import { useWorkbenchStore, NodeRef } from '../store/workbenchSlice'

// B45 Slice 2: the brainstorm chat as a permanent docked pane. Focus FOLLOWS the tree
// selection (toggleable lock) — select a scene, chat about that scene.
export function focusForNode(ref: NodeRef | null): BrainstormFocus | null {
  if (!ref) return null
  switch (ref.kind) {
    case 'concept': return { type: 'concept', name: 'concept' }
    case 'outline': return { type: 'concept', name: 'concept' }  // outline talk = concept-level talk
    case 'world': return { type: 'world', name: 'World' }
    case 'chapter': return { type: 'chapter', name: String(ref.n) }
    case 'scene': return { type: 'scene', name: `${ref.chapter}.${ref.scene}` }
    case 'milestone': return { type: 'arc', name: ref.arc }
    default: return { type: ref.kind, name: ref.name }
  }
}

export default function BrainstormPane({ projectName }: { projectName: string }) {
  const selection = useWorkbenchStore(s => s.selection)
  const focusFollow = useWorkbenchStore(s => s.focusFollow)
  const setFocusFollow = useWorkbenchStore(s => s.setFocusFollow)
  const setFocus = useBrainstormStore(s => s.setFocus)

  // Focus-follow: map the selected node to a chat focus. Light-touch — it only changes what
  // the NEXT message develops; sessions are not switched (use "Brainstorm this" for that).
  useEffect(() => {
    if (!focusFollow) return
    const f = focusForNode(selection)
    const cur = useBrainstormStore.getState().focus
    if (f && (!cur || cur.type !== f.type || cur.name !== f.name)) setFocus(f)
    if (!f && cur) setFocus(null)
  }, [selection, focusFollow, setFocus])

  return (
    <div className="h-[70vh] lg:h-[calc(100vh-150px)]">
      <BrainstormPanel
        projectName={projectName}
        variant="docked"
        headerExtra={
          <button onClick={() => setFocusFollow(!focusFollow)}
            title={focusFollow
              ? 'Focus follows your tree selection (click to lock the current focus)'
              : 'Focus is locked (click to follow the tree selection again)'}
            className={`p-1.5 ${focusFollow ? 'text-indigo-400' : 'text-amber-400'}`}>
            {focusFollow ? <Link2 size={14} /> : <Link2Off size={14} />}
          </button>
        }
      />
    </div>
  )
}
