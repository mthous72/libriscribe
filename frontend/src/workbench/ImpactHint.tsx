import { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import api from '../api/client'

// B45 Slice 5: the visible no-cascade guarantee — where this entity appears later, and a
// plain statement that editing here never regenerates anything.
export default function ImpactHint({ projectName, entityName }: { projectName: string, entityName: string }) {
  const [impact, setImpact] = useState<any>(null)

  useEffect(() => {
    let cancelled = false
    setImpact(null)
    api.get(`/projects/${projectName}/impact/${encodeURIComponent(entityName).replace(/%2F/gi, '/')}`)
      .then(r => { if (!cancelled) setImpact(r.data) })
      .catch(() => { if (!cancelled) setImpact(null) })
    return () => { cancelled = true }
  }, [projectName, entityName])

  if (!impact) return null
  const chapters: any[] = impact.chapters || []
  const scenes: any[] = impact.scenes || []
  if (chapters.length === 0 && scenes.length === 0) return null

  const chapterPart = chapters.map(c => `Ch. ${c.chapter} (${c.mentions}×)`).join(', ')
  const scenePart = scenes.map(s => `${s.chapter}.${s.scene}`).join(', ')

  return (
    <div className="mt-3 flex items-start gap-2 px-3 py-2 bg-gray-800/40 border border-gray-800 rounded-lg text-[11px] text-gray-400">
      <ShieldCheck size={13} className="shrink-0 mt-0.5 text-green-600" />
      <span>
        Referenced in{chapterPart ? <> prose: <span className="text-gray-300">{chapterPart}</span></> : null}
        {chapterPart && scenePart ? ' · ' : ''}
        {scenePart ? <>outline scenes: <span className="text-gray-300">{scenePart}</span></> : null}
        {' '}— editing here <span className="text-green-500">never regenerates</span> any of them.
      </span>
    </div>
  )
}
