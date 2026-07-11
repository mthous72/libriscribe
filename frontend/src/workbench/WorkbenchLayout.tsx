import { useCallback, useRef } from 'react'
import { useWorkbenchStore } from '../store/workbenchSlice'

// B45: three resizable panes — story tree | item editor | brainstorm. Widths persist via the
// store. Below lg the panes stack vertically (tree collapses to a <details>), so narrow
// viewports never scroll horizontally.
export default function WorkbenchLayout({ left, center, right }: {
  left: React.ReactNode, center: React.ReactNode, right: React.ReactNode,
}) {
  const [leftW, rightW] = useWorkbenchStore(s => s.paneWidths)
  const setPaneWidths = useWorkbenchStore(s => s.setPaneWidths)
  const rightOpen = useWorkbenchStore(s => s.rightOpen)
  const containerRef = useRef<HTMLDivElement>(null)

  const startDrag = useCallback((side: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const [l0, r0] = useWorkbenchStore.getState().paneWidths
    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - startX
      if (side === 'left') {
        setPaneWidths([Math.min(480, Math.max(180, l0 + dx)), r0])
      } else {
        setPaneWidths([l0, Math.min(640, Math.max(240, r0 - dx))])
      }
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [setPaneWidths])

  return (
    <div ref={containerRef}
      className="flex flex-col lg:grid gap-3 lg:gap-0 min-h-[70vh]"
      style={{
        gridTemplateColumns: rightOpen
          ? `${leftW}px 6px minmax(0,1fr) 6px ${rightW}px`
          : `${leftW}px 6px minmax(0,1fr)`,
      }}>
      {/* Tree — collapsible on small screens */}
      <details className="lg:hidden bg-gray-900 border border-gray-800 rounded-xl" open>
        <summary className="px-3 py-2 text-sm font-medium text-gray-300 cursor-pointer">Story tree</summary>
        <div className="p-2 max-h-[40vh] overflow-y-auto">{left}</div>
      </details>
      <div className="hidden lg:block overflow-y-auto pr-1 max-h-[calc(100vh-140px)]">{left}</div>

      <div className="hidden lg:block cursor-col-resize hover:bg-indigo-700/50 rounded"
        onMouseDown={startDrag('left')} title="Drag to resize" />

      <div className="min-w-0 max-h-none lg:max-h-[calc(100vh-140px)] lg:overflow-y-auto lg:px-1">{center}</div>

      {rightOpen && (
        <>
          <div className="hidden lg:block cursor-col-resize hover:bg-indigo-700/50 rounded"
            onMouseDown={startDrag('right')} title="Drag to resize" />
          <div className="min-w-0 lg:overflow-y-auto lg:max-h-[calc(100vh-140px)] lg:pl-1">{right}</div>
        </>
      )}
    </div>
  )
}
