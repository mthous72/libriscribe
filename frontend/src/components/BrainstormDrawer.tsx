import { useBrainstormStore } from '../store/brainstormSlice'
import BrainstormPanel from './BrainstormPanel'
import { MessageSquarePlus } from 'lucide-react'

// B45: thin overlay wrapper — ALL brainstorm logic lives in BrainstormPanel (shared with the
// workbench's docked pane). This drawer serves the non-workbench pages (wizard, lorebook…).
export default function BrainstormDrawer({ projectName }: { projectName: string }) {
  const { open, openBrainstorm, close } = useBrainstormStore()

  if (!open) {
    return (
      <button
        onClick={() => openBrainstorm()}
        title="Brainstorm with the AI (lore-aware)"
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-full shadow-lg text-sm font-medium"
      >
        <MessageSquarePlus size={16} /> Brainstorm
      </button>
    )
  }

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] shadow-2xl">
      <BrainstormPanel projectName={projectName} variant="drawer" onClose={close} />
    </div>
  )
}
