import type { WorkbenchTree } from '../api/client'
import type { NodeRef } from '../store/workbenchSlice'

// B45: the ordered walk. The story spine (concept → outline → ch1 → ch1.sc1… → ch2 …) is one
// sequence; lore/arc/thread nodes are section-local sequences appended after it, so Prev/Next
// always has somewhere sensible to go without mixing story order into reference material.
export function buildNavOrder(tree: WorkbenchTree | null): NodeRef[] {
  if (!tree) return []
  const order: NodeRef[] = [{ kind: 'concept' }, { kind: 'outline' }]
  for (const ch of tree.chapters) {
    order.push({ kind: 'chapter', n: ch.chapter_number })
    for (const sc of ch.scenes) {
      order.push({ kind: 'scene', chapter: ch.chapter_number, scene: sc.scene_number })
    }
  }
  for (const c of tree.characters) order.push({ kind: 'character', name: c.name })
  for (const l of tree.locations) order.push({ kind: 'location', name: l.name })
  for (const e of tree.lore) order.push({ kind: 'lore', name: e.name })
  order.push({ kind: 'world' })
  for (const a of tree.arcs) {
    order.push({ kind: 'arc', name: a.name })
    a.milestones.forEach((_, i) => order.push({ kind: 'milestone', arc: a.name, index: i }))
  }
  for (const t of tree.threads) order.push({ kind: 'thread', name: t.name })
  return order
}
