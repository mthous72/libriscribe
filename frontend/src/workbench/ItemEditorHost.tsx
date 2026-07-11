import type { WorkbenchTree } from '../api/client'
import type { NodeRef } from '../store/workbenchSlice'
import PrevNextBar from './PrevNextBar'
import GenerationStrip from './GenerationStrip'
import ConceptEditor from './editors/ConceptEditor'
import OutlineEditor from './editors/OutlineEditor'
import ChapterEditor from './editors/ChapterEditor'
import SceneEditor from './editors/SceneEditor'
import WorldEditor from './editors/WorldEditor'
import LoreEntityEditor from './editors/LoreEntityEditor'
import MilestoneView from './editors/MilestoneView'
import { buildNavOrder } from './navOrder'

// B45 center pane: switches on the selected node's kind; Prev/Next walks the story in order.
export default function ItemEditorHost({ projectName, tree, selection, onSelect }: {
  projectName: string, tree: WorkbenchTree, selection: NodeRef | null, onSelect: (ref: NodeRef) => void,
}) {
  const order = buildNavOrder(tree)
  const numChapters = tree.num_chapters || tree.chapters.length

  let body: React.ReactNode
  if (!selection) {
    body = (
      <div className="text-sm text-gray-500 space-y-2 py-8 text-center">
        <p>Select an item in the story tree — or walk the story in order with Prev/Next.</p>
        <p className="text-xs text-gray-600">Concept → Outline → Chapters → Scenes, then Lore, Arcs, and Threads.</p>
      </div>
    )
  } else {
    switch (selection.kind) {
      case 'concept': body = <ConceptEditor projectName={projectName} />; break
      case 'outline': body = <OutlineEditor projectName={projectName} />; break
      case 'world': body = <WorldEditor projectName={projectName} />; break
      case 'chapter': body = <ChapterEditor projectName={projectName} chapterNumber={selection.n} tree={tree} />; break
      case 'scene': body = <SceneEditor projectName={projectName} chapterNumber={selection.chapter} sceneNumber={selection.scene} tree={tree} />; break
      case 'milestone': body = <MilestoneView projectName={projectName} arcName={selection.arc} index={selection.index} tree={tree} />; break
      default:
        body = <LoreEntityEditor projectName={projectName} kind={selection.kind} entityName={selection.name} tree={tree} numChapters={numChapters} />
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <PrevNextBar order={order} selection={selection} onSelect={onSelect} />
      {body}
      <GenerationStrip />
    </div>
  )
}
