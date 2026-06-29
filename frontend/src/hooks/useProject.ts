import { useState, useEffect, useCallback } from 'react'
import { getProject, getProjectProgress } from '../api/client'

export function useProject(name: string | undefined) {
  const [project, setProject] = useState<any>(null)
  const [progress, setProgress] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!name) return
    try {
      const [p, prog] = await Promise.all([
        getProject(name),
        getProjectProgress(name),
      ])
      setProject(p)
      setProgress(prog)
    } catch (e) {
      console.error('Failed to load project:', e)
    } finally {
      setLoading(false)
    }
  }, [name])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { project, progress, loading, refresh }
}
